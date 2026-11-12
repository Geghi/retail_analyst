from agent_support import FakeWarehouse, ScriptedLlm, make_deps, plan_reply
from retail_analyst.agent import Agent


def test_an_off_topic_or_personal_data_request_is_refused_without_running_anything(tmp_path):
    llm = ScriptedLlm([plan_reply(intent="other")])
    warehouse = FakeWarehouse([])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("Show me the customer emails")

    assert reply.kind == "refusal"
    assert reply.text
    assert warehouse.sqls == []
    assert len(llm.calls) == 1


def test_a_model_written_query_for_personal_data_is_never_executed(tmp_path):
    llm = ScriptedLlm([plan_reply("SELECT email FROM users") for _ in range(3)])
    warehouse = FakeWarehouse([])
    agent = Agent("alice", make_deps(llm, warehouse, tmp_path))

    reply = agent.respond("List the emails of our best customers")

    assert reply.kind == "refusal"
    assert warehouse.sqls == []
    assert len(llm.calls) == 3
