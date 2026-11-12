from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from retail_analyst.agent.tracing import TraceCallback
from retail_analyst.observability import read_trace, start_turn


class UsageModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "usage-fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = AIMessage(
            content="ok",
            usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
            response_metadata={"model_name": "gemini-test"},
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_every_model_call_is_traced_with_its_token_usage(tmp_path):
    log = tmp_path / "trace.jsonl"
    turn = start_turn("alice", "question", log)

    UsageModel().invoke("hello", config={"callbacks": [TraceCallback(turn)]})

    (event,) = [e for e in read_trace(turn.trace_id, log) if e["event"] == "llm"]
    assert event["model"] == "gemini-test"
    assert event["input_tokens"] == 120
    assert event["output_tokens"] == 30
    assert event["total_tokens"] == 150
