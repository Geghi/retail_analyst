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
from retail_analyst.agent.replies import UNREADABLE
from retail_analyst.llm import LlmUnavailable
from retail_analyst.warehouse import WarehouseUnavailable

BUSY = WarehouseUnavailable("The data warehouse is busy, please try again in a moment.")


def test_a_transient_warehouse_error_is_retried_by_the_graph_and_then_succeeds(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Recovered.")])
    warehouse = FakeWarehouse([BUSY, BUSY, rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert len(warehouse.sqls) == 3


def test_a_warehouse_that_stays_down_gives_a_friendly_message_after_three_attempts(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL)])
    warehouse = FakeWarehouse([BUSY, BUSY, BUSY])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "error"
    assert reply.text == BUSY.user_message
    assert len(warehouse.sqls) == 3


def test_a_model_outage_gives_a_friendly_message_and_the_chat_keeps_working(tmp_path):
    outage = LlmUnavailable("The assistant is temporarily unavailable, please try again.")
    llm = ScriptedLlm([outage, plan_reply(REVENUE_SQL), analyst_reply("Back online.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    first = agent.respond("Revenue by category?")
    second = agent.respond("Revenue by category?")

    assert first.kind == "error"
    assert first.text == outage.user_message
    assert second.kind == "answer"
    assert second.text == "Back online."


def test_a_planner_reply_that_is_not_json_is_sent_back_for_correction(tmp_path):
    llm = ScriptedLlm(["Sure! Here is some prose.", plan_reply(REVENUE_SQL), analyst_reply("Ok.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert "valid JSON" in llm.calls[1]["prompt"]


def test_an_analyst_reply_that_is_plain_text_is_used_as_the_answer(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), "Jeans lead revenue."])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert reply.text == "Jeans lead revenue."


MALFORMED_ANALYST = (
    '{"answer": "Jeans lead.", "follow_up_queries": [], '
    '"findings": "### Summary\\In 2026, Jeans lead revenue.", '
    '"action_items": ["Restock Jeans", "Review Socks"]}'
)


def test_an_analyst_json_with_an_invalid_escape_and_extra_keys_still_shows_readable_text(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), MALFORMED_ANALYST])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert "{" not in reply.text
    assert "Jeans lead." in reply.text
    assert "Restock Jeans" in reply.text


def test_an_unreadable_analyst_json_is_asked_again_and_the_second_reply_is_used(tmp_path):
    broken = '{"answer": "Jeans lead.", "follow_up_queries": [ oops'
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), broken, analyst_reply("Jeans lead.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.text == "Jeans lead."
    assert "valid JSON" in llm.calls[2]["prompt"]


def test_an_analyst_that_keeps_returning_broken_json_gives_a_fixed_message_after_the_retries(
    tmp_path,
):
    broken = '{"answer": "Jeans lead.", "follow_up_queries": [ oops'
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), broken, broken, broken])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.text == UNREADABLE
    assert len(llm.calls) == 4
