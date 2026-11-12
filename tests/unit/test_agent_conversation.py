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
from retail_analyst.warehouse import QueryTooExpensive

JEANS_ROW = rows_result([{"category": "Jeans", "revenue": 1.0}])
DRILL_SQL = "SELECT brand, COUNT(*) AS items FROM products GROUP BY brand"


def test_a_question_about_the_data_is_answered_from_the_schema_without_queries(tmp_path):
    reply_text = "You can analyse orders, items, products and shopper demographics."
    llm = ScriptedLlm([plan_reply(intent="schema_question", reply=reply_text)])
    warehouse = FakeWarehouse([])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("What data do we have?")

    assert reply.kind == "answer"
    assert reply.text == reply_text
    assert warehouse.sqls == []


def test_a_follow_up_question_sees_the_conversation_so_far(tmp_path):
    llm = ScriptedLlm(
        [
            plan_reply(REVENUE_SQL),
            analyst_reply("Jeans lead."),
            plan_reply(REVENUE_SQL),
            analyst_reply("Ok."),
        ]
    )
    agent = Agent("alice", make_deps(llm, FakeWarehouse([JEANS_ROW, JEANS_ROW]), tmp_path))

    agent.respond("Revenue by category?")
    agent.respond("And what about sweaters?")

    second_plan_prompt = llm.calls[2]["prompt"]
    assert "Revenue by category?" in second_plan_prompt
    assert "Jeans lead." in second_plan_prompt


def test_the_analyst_can_ask_for_one_follow_up_query_and_answers_with_both_results(tmp_path):
    llm = ScriptedLlm(
        [
            plan_reply(REVENUE_SQL),
            analyst_reply("Need brands.", follow_up=[DRILL_SQL]),
            analyst_reply("Final."),
        ]
    )
    warehouse = FakeWarehouse([JEANS_ROW, rows_result([{"brand": "Levi", "items": 3}])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Why did revenue change?")

    assert reply.text == "Final."
    assert len(warehouse.sqls) == 2
    final_prompt = llm.calls[2]["prompt"]
    assert "Jeans" in final_prompt and "Levi" in final_prompt


def test_follow_up_rounds_are_capped_at_three_query_rounds(tmp_path):
    ask_more = analyst_reply("More.", follow_up=[DRILL_SQL])
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), ask_more, ask_more, ask_more])
    warehouse = FakeWarehouse([JEANS_ROW, JEANS_ROW, JEANS_ROW])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Why did revenue change?")

    assert reply.kind == "answer"
    assert len(warehouse.sqls) == 3
    assert len(llm.calls) == 4


def test_an_empty_result_gets_one_broadening_hint_then_the_analyst_answers(tmp_path):
    llm = ScriptedLlm(
        [plan_reply(REVENUE_SQL), plan_reply(REVENUE_SQL), analyst_reply("Nothing found.")]
    )
    warehouse = FakeWarehouse([rows_result([]), rows_result([])])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.text == "Nothing found."
    assert "no rows" in llm.calls[1]["prompt"]
    assert len(warehouse.sqls) == 2


def test_an_over_budget_query_is_sent_back_to_be_narrowed(tmp_path):
    too_big = QueryTooExpensive("This query would scan too much data. Narrow the period.")
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), plan_reply(REVENUE_SQL), analyst_reply("Ok.")])
    agent = Agent("alice", make_deps(llm, FakeWarehouse([too_big, JEANS_ROW]), tmp_path))

    reply = agent.respond("Revenue by category?")

    assert reply.kind == "answer"
    assert "scan too much data" in llm.calls[1]["prompt"]
