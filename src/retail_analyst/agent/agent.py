import uuid
from dataclasses import dataclass

import psycopg
from langgraph.types import Command

from retail_analyst import observability
from retail_analyst.llm import LlmUnavailable
from retail_analyst.warehouse import WarehouseError

from .deps import AgentDeps
from .graph import build_graph
from .limits import HISTORY_MESSAGES
from .tracing import TraceCallback


@dataclass(frozen=True)
class Reply:
    kind: str
    text: str
    trace_id: str


REPORTS_DOWN_TEXT = "Saved reports are temporarily unavailable. Please try again in a moment."
KINDS = {"answered": "answer", "error": "error", "refused": "refusal"}


class Agent:
    def __init__(self, user_id: str, deps: AgentDeps | None = None):
        self.user_id = user_id
        self.deps = deps or AgentDeps()
        self.conversation_id = str(uuid.uuid4())
        self.graph = build_graph(self.deps)
        self.history: list[str] = []

    def respond(self, message: str) -> Reply:
        turn = observability.start_turn(self.user_id, message, self.deps.log_path)
        config = {
            "configurable": {"thread_id": self.conversation_id, "turn": turn},
            "callbacks": [TraceCallback(turn)],
        }
        resuming = bool(self.graph.get_state(config).interrupts)
        payload = Command(resume=message) if resuming else self.new_turn_input(message)
        try:
            state = self.graph.invoke(payload, config)
        except (LlmUnavailable, WarehouseError) as error:
            turn.finish("error", error=type(error).__name__)
            return Reply(kind="error", text=error.user_message, trace_id=turn.trace_id)
        except psycopg.Error as error:
            turn.finish("error", error=type(error).__name__)
            return Reply(kind="error", text=REPORTS_DOWN_TEXT, trace_id=turn.trace_id)
        if state.get("__interrupt__"):
            turn.finish("needs_confirmation")
            prompt = state["__interrupt__"][0].value
            return Reply(kind="needs_confirmation", text=prompt, trace_id=turn.trace_id)
        turn.finish(state["outcome"])
        reply = Reply(kind=KINDS[state["outcome"]], text=state["answer"], trace_id=turn.trace_id)
        self.remember(message, reply)
        return reply

    def remember(self, message: str, reply: Reply) -> None:
        if reply.kind in ("answer", "refusal"):
            self.history += [f"User: {message}", f"Assistant: {reply.text}"]

    def new_turn_input(self, message: str) -> dict:
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "question": message,
            "queries": [],
            "results": [],
            "feedback": [],
            "corrections": 0,
            "rounds": 0,
            "more": False,
            "empty_retried": False,
            "history": self.history[-HISTORY_MESSAGES:],
        }
