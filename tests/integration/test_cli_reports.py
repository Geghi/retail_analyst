import uuid

import pytest

from agent_support import FakeWarehouse, ScriptedLlm, make_deps
from retail_analyst.agent import Agent
from retail_analyst.cli import run_chat
from retail_analyst.reports import save_report
from retail_analyst.storage import connect, create_tables

URL = "postgresql://analyst:analyst@localhost:5432/analyst"


@pytest.fixture(scope="module")
def conn():
    connection = connect(URL)
    create_tables(connection)
    yield connection
    connection.close()


def chat(agent, *lines):
    typed = iter(lines)
    shown = []

    def read(prompt):
        try:
            return next(typed)
        except StopIteration:
            raise EOFError from None

    run_chat(agent, read=read, write=shown.append)
    return "\n".join(shown)


def test_reports_lists_my_saved_reports_and_not_other_users(conn, tmp_path):
    mine, theirs = f"user-{uuid.uuid4()}", f"user-{uuid.uuid4()}"
    save_report(conn, mine, "October revenue", "body", str(uuid.uuid4()))
    save_report(conn, theirs, "Secret plan", "body", str(uuid.uuid4()))
    agent = Agent(mine, make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=conn))

    output = chat(agent, "/reports")

    assert "October revenue" in output
    assert "Secret plan" not in output


def test_reports_with_none_saved_says_so(conn, tmp_path):
    agent = Agent(
        f"user-{uuid.uuid4()}", make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=conn)
    )

    assert "No saved reports" in chat(agent, "/reports")


def test_reports_with_the_database_down_says_so_and_the_chat_continues(tmp_path):
    down = connect(URL)
    down.close()
    agent = Agent("alice", make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=down))

    output = chat(agent, "/reports", "/trace")

    assert "temporarily unavailable" in output
    assert "No questions asked yet" in output


def test_starting_the_cli_for_a_valid_user_greets_and_exits_cleanly():
    from retail_analyst.cli import main

    shown = []
    env = {
        "GEMINI_API_KEY": "k",
        "GEMINI_MODEL": "main-model",
        "GEMINI_FALLBACK_MODEL": "fallback-model",
        "GCP_PROJECT_ID": "p",
        "DATABASE_URL": URL,
    }

    code = main(["--user", "alice"], env=env, read=lambda prompt: "exit", write=shown.append)

    assert code == 0
    assert "Chatting as alice" in shown[0]


def test_a_listed_report_opens_by_number_and_enter_goes_back_to_the_chat(conn, tmp_path):
    mine = f"user-{uuid.uuid4()}"
    save_report(conn, mine, "October revenue", "Jeans lead in October.", str(uuid.uuid4()))
    save_report(conn, mine, "Churn review", "Churn fell.", str(uuid.uuid4()))
    agent = Agent(mine, make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=conn))

    output = chat(agent, "/reports", "2", "", "/trace")

    assert "1. October revenue" in output and "2. Churn review" in output
    assert "Churn fell." in output
    assert "Jeans lead in October." not in output
    assert "No questions asked yet" in output


def test_a_report_number_that_does_not_exist_is_reported_and_the_list_stays_open(conn, tmp_path):
    mine = f"user-{uuid.uuid4()}"
    save_report(conn, mine, "October revenue", "Jeans lead in October.", str(uuid.uuid4()))
    agent = Agent(mine, make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=conn))

    output = chat(agent, "/reports", "9", "1", "")

    assert "There is no report number 9" in output
    assert "Jeans lead in October." in output


def test_a_line_typed_at_the_report_prompt_that_is_not_a_number_runs_as_a_normal_command(
    conn, tmp_path
):
    mine = f"user-{uuid.uuid4()}"
    save_report(conn, mine, "October revenue", "Jeans lead in October.", str(uuid.uuid4()))
    agent = Agent(mine, make_deps(ScriptedLlm([]), FakeWarehouse([]), tmp_path, conn=conn))

    output = chat(agent, "/reports", "/trace")

    assert "No questions asked yet" in output
