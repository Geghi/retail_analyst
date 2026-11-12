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
from retail_analyst.warehouse import QueryFailed

BROKEN_SQL = "SELECT revnue FROM products"
BIGQUERY_COMPLAINT = "Unrecognized name: revnue"


def failing_warehouse(times):
    return FakeWarehouse(
        [QueryFailed("The query failed.", BIGQUERY_COMPLAINT) for _ in range(times)]
    )


def test_a_failed_query_is_fixed_after_the_error_is_sent_back_to_the_model(tmp_path):
    llm = ScriptedLlm([plan_reply(BROKEN_SQL), plan_reply(REVENUE_SQL), analyst_reply("Fixed.")])
    warehouse = failing_warehouse(1)
    warehouse.replies.append(rows_result([{"category": "Jeans", "revenue": 1.0}]))
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert reply.text == "Fixed."
    assert BIGQUERY_COMPLAINT in llm.calls[1]["prompt"]
    assert len(warehouse.sqls) == 2


def test_endless_failures_stop_after_two_corrections_with_a_plain_message(tmp_path):
    llm = ScriptedLlm([plan_reply(BROKEN_SQL) for _ in range(3)])
    warehouse = failing_warehouse(3)
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "error"
    assert reply.text
    assert BIGQUERY_COMPLAINT not in reply.text
    assert len(llm.calls) == 3
    assert len(warehouse.sqls) == 3
