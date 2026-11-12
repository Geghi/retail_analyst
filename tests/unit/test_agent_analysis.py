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


def test_a_question_runs_the_scoped_query_and_the_analyst_only_sees_masked_rows(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead revenue.")])
    warehouse = FakeWarehouse(
        [rows_result([{"category": "Jeans", "revenue": 100.0, "note": "write to boss@corp.com"}])]
    )
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("What is revenue by category?")

    assert reply.kind == "answer"
    assert reply.text == "Jeans lead revenue."
    assert "category IN ('Jeans')" in warehouse.sqls[0]
    analyst_prompt = llm.calls[1]["prompt"]
    assert "boss@corp.com" not in analyst_prompt
    assert "[REDACTED]" in analyst_prompt
