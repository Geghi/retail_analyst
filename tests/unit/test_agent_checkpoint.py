import logging

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


def test_the_saved_conversation_state_holds_only_plain_data(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    llm = ScriptedLlm(
        [plan_reply(REVENUE_SQL), analyst_reply("Jeans lead."), plan_reply(intent="other")]
    )
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    agent.respond("Revenue by category?")
    agent.respond("And the weather?")

    assert "unregistered type" not in caplog.text
