from langgraph.graph import END

from retail_analyst import knowledge
from retail_analyst.guardrails import GuardrailViolation, mask_rows, validate_sql
from retail_analyst.warehouse import QueryFailed, QueryTooExpensive

from .deps import AgentDeps
from .limits import MAX_CORRECTIONS, MAX_QUERY_ROUNDS
from .prompts import analyst_prompt, analyst_system, planner_prompt, planner_system
from .replies import ReplyFormatError, parse_json_reply
from .state import AgentState
from .texts import EMPTY_HINT, GIVE_UP_TEXT, NOT_JSON, REFUSAL_TEXT, SCHEMA_FALLBACK

PLAN_ROUTES = {
    "analysis": "run_queries",
    "schema_question": "schema_answer",
    "smalltalk": "schema_answer",
    "save_report": "save_report",
    "delete_reports": "request_delete",
}


class AnalysisNodes:
    def __init__(self, deps: AgentDeps):
        self.deps = deps

    def load_context(self, state: AgentState) -> dict:
        similar = self.deps.find_similar(state["question"])
        return {
            "persona": self.deps.load_persona(),
            "today": self.deps.today().isoformat(),
            "trios_text": knowledge.format_for_prompt(similar) if similar else "none",
        }

    def plan(self, state: AgentState, config) -> dict:
        feedback = state.get("feedback", [])
        if feedback:
            config["configurable"]["turn"].event(
                "retry", attempt=state["corrections"], errors=feedback
            )
        system = planner_system(state["today"], state["trios_text"])
        prompt = planner_prompt(state["question"], feedback, state.get("history", []))
        try:
            reply = parse_json_reply(self.deps.generate(prompt, system=system, config=config))
        except ReplyFormatError:
            return {
                "plan_failed": True,
                "feedback": [{"sql": "(your previous reply)", "error": NOT_JSON, "blocked": False}],
                "corrections": state.get("corrections", 0) + 1,
            }
        return {
            "plan_failed": False,
            "intent": reply.get("intent", "other"),
            "queries": list(reply.get("queries", [])),
            "delete": reply.get("delete") or {},
            "reply": str(reply.get("reply", "")),
        }

    def after_plan(self, state: AgentState) -> str:
        if state["plan_failed"]:
            return self.retry_or_give_up(state)
        return PLAN_ROUTES.get(state["intent"], "refuse")

    def run_queries(self, state: AgentState, config) -> dict:
        turn = config["configurable"]["turn"]
        scope = self.deps.load_scope(state["user_id"])
        attempts = [self.attempt(sql, scope, turn) for sql in state["queries"]]
        failures = [failure for _, failure in attempts if failure]
        if failures:
            return {"feedback": failures, "corrections": state.get("corrections", 0) + 1}
        fresh = [result for result, _ in attempts]
        if self.worth_a_broader_query(state, fresh):
            hint = {"sql": "; ".join(state["queries"]), "error": EMPTY_HINT, "blocked": False}
            return {"feedback": [hint], "empty_retried": True}
        return {"results": state.get("results", []) + fresh, "feedback": []}

    def attempt(self, sql: str, scope, turn):
        try:
            safe_sql = validate_sql(sql, scope)
            result = self.deps.run_query(safe_sql)
        except GuardrailViolation as error:
            return None, self.failure(turn, sql, str(error), blocked=True)
        except QueryFailed as error:
            return None, self.failure(turn, sql, error.reason, blocked=False)
        except QueryTooExpensive as error:
            return None, self.failure(turn, sql, error.user_message, blocked=False)
        turn.event("query", sql=safe_sql, ok=True, rows=len(result.rows))
        return {"sql": sql, "rows": mask_rows(result.rows)}, None

    def failure(self, turn, sql: str, error: str, blocked: bool) -> dict:
        turn.event("query", sql=sql, ok=False, blocked=blocked, error=error)
        return {"sql": sql, "error": error, "blocked": blocked}

    def worth_a_broader_query(self, state: AgentState, fresh: list[dict]) -> bool:
        first_round = state.get("rounds", 0) == 0
        all_empty = all(not item["rows"] for item in fresh)
        return bool(fresh) and first_round and all_empty and not state.get("empty_retried")

    def after_run(self, state: AgentState) -> str:
        return self.retry_or_give_up(state) if state["feedback"] else "analyze"

    def retry_or_give_up(self, state: AgentState) -> str:
        return "plan" if state["corrections"] <= MAX_CORRECTIONS else "give_up"

    def analyze(self, state: AgentState, config) -> dict:
        system = analyst_system(state["persona"], state["today"])
        prompt = analyst_prompt(state["question"], state["results"])
        text = self.deps.generate(prompt, system=system, config=config)
        try:
            parsed = parse_json_reply(text)
            answer, follow_ups = str(parsed["answer"]), list(parsed.get("follow_up_queries") or [])
        except (ReplyFormatError, KeyError):
            answer, follow_ups = text, []
        rounds = state.get("rounds", 0) + 1
        more = bool(follow_ups) and rounds < MAX_QUERY_ROUNDS
        update = {"answer": answer, "last_answer": answer, "outcome": "answered"}
        update["last_question"] = state["question"]
        update.update({"rounds": rounds, "more": more})
        if more:
            update.update({"queries": follow_ups, "corrections": 0, "feedback": []})
        return update

    def after_analyze(self, state: AgentState) -> str:
        return "run_queries" if state["more"] else END

    def schema_answer(self, state: AgentState) -> dict:
        return {"answer": state.get("reply") or SCHEMA_FALLBACK, "outcome": "answered"}

    def give_up(self, state: AgentState) -> dict:
        if any(item["blocked"] for item in state["feedback"]):
            return self.refuse(state)
        return {"answer": GIVE_UP_TEXT, "outcome": "error"}

    def refuse(self, state: AgentState) -> dict:
        return {"answer": REFUSAL_TEXT, "outcome": "refused"}
