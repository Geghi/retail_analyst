from agent_support import (
    REVENUE_SQL,
    FakeWarehouse,
    ScriptedLlm,
    analyst_reply,
    make_deps,
    plan_reply,
    rows_result,
)
from retail_analyst.agent import Agent
from retail_analyst.observability import read_trace
from retail_analyst.warehouse import QueryFailed


def names(events):
    return [event["event"] for event in events]


def test_a_turn_leaves_a_trace_with_its_steps_the_executed_sql_and_the_outcome(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    deps = make_deps(llm, warehouse, tmp_path)

    reply = Agent("alice", deps).respond("Revenue by category?")

    events = read_trace(reply.trace_id, deps.log_path)
    assert names(events)[0] == "turn_started"
    assert names(events)[-1] == "turn_finished"
    assert events[-1]["outcome"] == "answered"
    for step in ("plan", "run_queries", "analyze"):
        finished = [e for e in events if e["event"] == step]
        assert finished and finished[0]["ok"] is True and "duration_ms" in finished[0]
    query = next(e for e in events if e["event"] == "query")
    assert "category IN ('Jeans')" in query["sql"]
    assert query["rows"] == 1


def test_a_correction_is_traced_as_a_retry_with_the_reason(tmp_path):
    llm = ScriptedLlm(
        [plan_reply("SELECT revnue FROM products"), plan_reply(REVENUE_SQL), analyst_reply("Ok.")]
    )
    warehouse = FakeWarehouse(
        [
            QueryFailed("failed", "Unrecognized name: revnue"),
            rows_result([{"category": "Jeans", "revenue": 1.0}]),
        ]
    )
    deps = make_deps(llm, warehouse, tmp_path)

    reply = Agent("alice", deps).respond("Revenue by category?")

    events = read_trace(reply.trace_id, deps.log_path)
    retry = next(e for e in events if e["event"] == "retry")
    assert "Unrecognized name: revnue" in str(retry)


def test_refused_and_failed_turns_record_their_outcome(tmp_path):
    llm = ScriptedLlm([plan_reply(intent="other")])
    deps = make_deps(llm, FakeWarehouse([]), tmp_path)

    reply = Agent("alice", deps).respond("Tell me a joke")

    assert read_trace(reply.trace_id, deps.log_path)[-1]["outcome"] == "refused"


def test_an_api_key_typed_by_the_user_never_reaches_the_log(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-secret-12345")
    llm = ScriptedLlm([plan_reply(intent="other")])
    deps = make_deps(llm, FakeWarehouse([]), tmp_path)

    Agent("alice", deps).respond("my key is sk-secret-12345, please use it")

    assert "sk-secret-12345" not in deps.log_path.read_text()
