import json

from test_agent_tokens import UsageModel

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
from retail_analyst.agent.tracing import TraceCallback
from retail_analyst.observability import read_trace, start_turn


def llm_events(tmp_path):
    log = tmp_path / "trace.jsonl"
    turn = start_turn("alice", "question", log)
    UsageModel().invoke("hello there", config={"callbacks": [TraceCallback(turn)]})
    return read_trace(turn.trace_id, log)


def test_verbose_tracing_records_the_prompt_and_the_raw_answer_of_each_model_call(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TRACE_VERBOSE", "1")

    events = llm_events(tmp_path)

    (sent,) = [e for e in events if e["event"] == "llm_input"]
    (received,) = [e for e in events if e["event"] == "llm"]
    assert "hello there" in sent["prompt"]
    assert received["output"] == "ok"


def test_by_default_no_prompt_or_answer_text_reaches_the_trace(tmp_path, monkeypatch):
    monkeypatch.delenv("TRACE_VERBOSE", raising=False)

    events = llm_events(tmp_path)

    assert not [e for e in events if e["event"] == "llm_input"]
    (received,) = [e for e in events if e["event"] == "llm"]
    assert "output" not in received


def run_revenue_question(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    Agent("alice", make_deps(llm, warehouse, tmp_path)).respond("Revenue by category?")
    lines = (tmp_path / "trace.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_verbose_tracing_records_the_rows_each_query_returned(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACE_VERBOSE", "1")

    (query,) = [e for e in run_revenue_question(tmp_path) if e["event"] == "query"]

    assert query["data"] == [{"category": "Jeans", "revenue": 1.0}]


def test_by_default_query_rows_are_not_written_to_the_trace(tmp_path, monkeypatch):
    monkeypatch.delenv("TRACE_VERBOSE", raising=False)

    (query,) = [e for e in run_revenue_question(tmp_path) if e["event"] == "query"]

    assert "data" not in query
