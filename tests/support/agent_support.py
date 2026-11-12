import json
from datetime import date

from retail_analyst.agent import AgentDeps
from retail_analyst.guardrails import UserScope
from retail_analyst.warehouse import QueryResult

ALICE = UserScope(user_id="alice", allowed_categories=frozenset({"Jeans"}))
REVENUE_SQL = (
    "SELECT p.category, SUM(oi.sale_price) AS revenue "
    "FROM order_items oi JOIN products p ON oi.product_id = p.id GROUP BY p.category"
)


class Scripted:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def respond(self, call):
        self.calls.append(call)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class ScriptedLlm(Scripted):
    def __call__(self, prompt, *, system=None, config=None):
        return self.respond({"system": system, "prompt": prompt})


class FakeWarehouse(Scripted):
    def __call__(self, sql, **kwargs):
        return self.respond(sql)

    @property
    def sqls(self):
        return self.calls


def plan_reply(*queries, intent="analysis", **extra):
    return json.dumps({"intent": intent, "queries": list(queries), **extra})


def analyst_reply(text, follow_up=()):
    return json.dumps({"answer": text, "follow_up_queries": list(follow_up)})


def rows_result(rows):
    return QueryResult(rows=rows, bytes_billed=0, is_empty=not rows)


def make_deps(llm, warehouse, tmp_path, **overrides):
    values = {
        "generate": llm,
        "run_query": warehouse,
        "load_scope": lambda user_id: ALICE,
        "load_persona": lambda: "Be concise.",
        "find_similar": lambda question: [],
        "today": lambda: date(2026, 11, 12),
        "log_path": tmp_path / "trace.jsonl",
        "conn": None,
        "retry_interval": 0.0,
    }
    values.update(overrides)
    return AgentDeps(**values)
