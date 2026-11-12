import uuid

import pytest

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
from retail_analyst.reports import list_reports, save_report
from retail_analyst.storage import connect, create_tables

URL = "postgresql://analyst:analyst@localhost:5432/analyst"
DELETE_X = plan_reply(
    intent="delete_reports", delete={"text_match": "Client X", "this_conversation": False}
)


@pytest.fixture(scope="module")
def conn():
    connection = connect(URL)
    create_tables(connection)
    yield connection
    connection.close()


def new_agent(conn, tmp_path, llm_replies, warehouse=None):
    user = f"user-{uuid.uuid4()}"
    llm = ScriptedLlm(llm_replies)
    deps = make_deps(llm, warehouse or FakeWarehouse([]), tmp_path, conn=conn)
    return user, llm, Agent(user, deps)


def seed(conn, user, *bodies, conversation_id=None):
    return [
        save_report(conn, user, f"Report {i}", body, conversation_id or str(uuid.uuid4()))
        for i, body in enumerate(bodies)
    ]


def titles(conn, user):
    return sorted(report.title for report in list_reports(conn, user))


def test_save_stores_the_last_report_for_the_user_and_conversation(conn, tmp_path):
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    replies = [
        plan_reply(REVENUE_SQL),
        analyst_reply("# Q1 report\nJeans lead."),
        plan_reply(intent="save_report"),
    ]
    user, _, agent = new_agent(conn, tmp_path, replies, warehouse)

    agent.respond("Create a Q1 report")
    saved = agent.respond("Save this report")

    stored = list_reports(conn, user)
    assert saved.kind == "answer"
    assert [r.body for r in stored] == ["# Q1 report\nJeans lead."]
    assert stored[0].conversation_id == agent.conversation_id


def test_save_without_a_report_says_there_is_nothing_to_save(conn, tmp_path):
    user, _, agent = new_agent(conn, tmp_path, [plan_reply(intent="save_report")])

    reply = agent.respond("Save this report")

    assert reply.kind == "answer"
    assert list_reports(conn, user) == []


def test_delete_asks_first_then_deletes_exactly_the_listed_reports_on_yes(conn, tmp_path):
    user, llm, agent = new_agent(conn, tmp_path, [DELETE_X])
    seed(conn, user, "About Client X", "client x again", "About Client Y")

    asked = agent.respond("Delete all reports mentioning Client X")

    assert asked.kind == "needs_confirmation"
    assert "Report 0" in asked.text and "Report 1" in asked.text and "Report 2" not in asked.text
    assert len(list_reports(conn, user)) == 3

    done = agent.respond("yes")

    assert done.kind == "answer"
    assert titles(conn, user) == ["Report 2"]
    assert len(llm.calls) == 1


def test_no_cancels_and_nothing_is_deleted(conn, tmp_path):
    user, _, agent = new_agent(conn, tmp_path, [DELETE_X])
    seed(conn, user, "About Client X")

    agent.respond("Delete all reports mentioning Client X")
    reply = agent.respond("no")

    assert reply.kind == "answer"
    assert len(list_reports(conn, user)) == 1


def test_an_unclear_answer_asks_again_and_deletes_nothing(conn, tmp_path):
    user, _, agent = new_agent(conn, tmp_path, [DELETE_X])
    seed(conn, user, "About Client X")

    agent.respond("Delete all reports mentioning Client X")
    unclear = agent.respond("hmm maybe")

    assert unclear.kind == "needs_confirmation"
    assert len(list_reports(conn, user)) == 1
    agent.respond("yes")
    assert list_reports(conn, user) == []


def test_nothing_matching_is_reported_without_asking_for_confirmation(conn, tmp_path):
    user, _, agent = new_agent(conn, tmp_path, [DELETE_X])
    seed(conn, user, "About Client Y")

    reply = agent.respond("Delete all reports mentioning Client X")

    assert reply.kind == "answer"
    assert len(list_reports(conn, user)) == 1


def test_this_conversation_deletes_only_reports_made_in_it(conn, tmp_path):
    plan = plan_reply(intent="delete_reports", delete={"text_match": "", "this_conversation": True})
    user, _, agent = new_agent(conn, tmp_path, [plan])
    seed(conn, user, "here one", "here two", conversation_id=agent.conversation_id)
    seed(conn, user, "elsewhere")

    asked = agent.respond("Delete all the reports we made in this conversation")
    agent.respond("yes")

    assert asked.kind == "needs_confirmation"
    assert [r.body for r in list_reports(conn, user)] == ["elsewhere"]


def test_when_the_reports_database_is_down_saving_says_so_and_analysis_still_works(tmp_path):
    down = connect(URL)
    down.close()
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])] * 2)
    replies = [
        plan_reply(REVENUE_SQL),
        analyst_reply("# Report\nJeans lead."),
        plan_reply(intent="save_report"),
        plan_reply(REVENUE_SQL),
        analyst_reply("Still working."),
    ]
    _, _, agent = new_agent(down, tmp_path, replies, warehouse)

    agent.respond("Create a report")
    saved = agent.respond("Save this report")
    after = agent.respond("Revenue again?")

    assert saved.kind == "error"
    assert "saved reports" in saved.text.lower()
    assert "OperationalError" not in saved.text
    assert after.kind == "answer"
    assert after.text == "Still working."
