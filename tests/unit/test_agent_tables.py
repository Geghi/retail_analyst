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

DRILL_SQL = "SELECT brand, COUNT(*) AS items FROM products GROUP BY brand"


def test_an_answer_carries_the_rows_of_the_query_next_to_the_text(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead.")])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.text == "Jeans lead."
    assert reply.tables == ([{"category": "Jeans", "revenue": 1.0}],)


def test_the_rows_shown_to_the_user_are_masked_like_the_ones_the_model_sees(tmp_path):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Done.")])
    warehouse = FakeWarehouse(
        [rows_result([{"category": "Jeans", "note": "mail jane@example.com"}])]
    )
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert "jane@example.com" not in str(reply.tables)
    assert "[REDACTED]" in str(reply.tables)


def test_every_query_the_answer_used_gets_its_own_table(tmp_path):
    llm = ScriptedLlm(
        [
            plan_reply(REVENUE_SQL),
            analyst_reply("Need brands.", follow_up=[DRILL_SQL]),
            analyst_reply("Final."),
        ]
    )
    warehouse = FakeWarehouse(
        [
            rows_result([{"category": "Jeans", "revenue": 1.0}]),
            rows_result([{"brand": "Levi", "items": 3}]),
        ]
    )
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Why did revenue change?")

    assert reply.tables == (
        [{"category": "Jeans", "revenue": 1.0}],
        [{"brand": "Levi", "items": 3}],
    )


def test_an_answer_without_queries_has_no_tables(tmp_path):
    llm = ScriptedLlm([plan_reply(intent="schema_question", reply="Orders and items.")])
    agent = Agent("alice", make_deps(llm, FakeWarehouse([]), tmp_path))

    reply = agent.respond("What data do we have?")

    assert reply.tables == ()
