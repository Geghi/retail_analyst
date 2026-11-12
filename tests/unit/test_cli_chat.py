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
from retail_analyst.cli import run_chat


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


def revenue_agent(tmp_path, *extra_replies):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead."), *extra_replies])
    warehouse = FakeWarehouse([rows_result([{"category": "Jeans", "revenue": 1.0}])])
    return Agent("alice", make_deps(llm, warehouse, tmp_path))


def test_a_typed_question_is_answered_and_exit_ends_the_chat(tmp_path):
    output = chat(revenue_agent(tmp_path), "Revenue by category?", "exit")

    assert "Jeans lead." in output


def test_blank_lines_are_ignored_and_ctrl_d_ends_the_chat(tmp_path):
    agent = revenue_agent(tmp_path)

    output = chat(agent, "", "   ")

    assert agent.deps.generate.calls == []
    assert "Jeans" not in output


def test_trace_shows_the_steps_of_the_last_answer(tmp_path):
    output = chat(revenue_agent(tmp_path), "Revenue by category?", "/trace")

    assert "plan" in output
    assert "run_queries" in output
    assert "analyze" in output


def test_trace_before_any_question_says_there_is_nothing_yet(tmp_path):
    output = chat(revenue_agent(tmp_path), "/trace")

    assert "No questions asked yet" in output
