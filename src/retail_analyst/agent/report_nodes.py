import uuid

from langgraph.graph import END
from langgraph.types import interrupt

from retail_analyst import reports

from .deps import AgentDeps
from .report_text import (
    CANCELLED,
    EXPIRED,
    NO,
    NO_MATCH,
    NOTHING_TO_SAVE,
    YES,
    deletion_prompt,
    normalize_answer,
    report_title,
)
from .state import AgentState


class ReportNodes:
    def __init__(self, deps: AgentDeps):
        self.deps = deps

    def save_report(self, state: AgentState) -> dict:
        body = state.get("last_answer")
        if not body:
            return {"answer": NOTHING_TO_SAVE, "outcome": "answered"}
        saved = reports.save_report(
            self.deps.conn, state["user_id"], report_title(body), body, state["conversation_id"]
        )
        return {"answer": f'Saved the report "{saved.title}".', "outcome": "answered"}

    def request_delete(self, state: AgentState) -> dict:
        spec = state.get("delete") or {}
        conversation = state["conversation_id"] if spec.get("this_conversation") else None
        try:
            pending = reports.request_delete(
                self.deps.conn,
                state["user_id"],
                text_match=spec.get("text_match") or None,
                conversation_id=conversation,
            )
        except reports.NothingToDelete:
            return {"answer": NO_MATCH, "outcome": "answered", "pending_id": ""}
        titles = [report.title for report in pending.reports]
        return {"pending_id": str(pending.id), "delete_prompt": deletion_prompt(titles)}

    def after_request(self, state: AgentState) -> str:
        return "confirm" if state["pending_id"] else END

    def confirm(self, state: AgentState) -> dict:
        pending_id = uuid.UUID(state["pending_id"])
        prompt = state["delete_prompt"]
        while True:
            decision = normalize_answer(interrupt(prompt))
            if decision in YES:
                return self.execute_delete(state, pending_id)
            if decision in NO:
                reports.cancel_delete(self.deps.conn, state["user_id"], pending_id)
                return {"answer": CANCELLED, "outcome": "answered"}
            prompt = "Please answer yes or no.\n" + state["delete_prompt"]

    def execute_delete(self, state: AgentState, pending_id: uuid.UUID) -> dict:
        try:
            deleted = reports.confirm_delete(self.deps.conn, state["user_id"], pending_id)
        except reports.PendingNotFound:
            return {"answer": EXPIRED, "outcome": "answered"}
        return {"answer": f"Deleted {len(deleted)} saved report(s).", "outcome": "answered"}
