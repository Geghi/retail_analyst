from typing import TypedDict

from retail_analyst.guardrails import UserScope


class AgentState(TypedDict, total=False):
    user_id: str
    conversation_id: str
    question: str
    scope: UserScope
    persona: str
    today: str
    trios_text: str
    intent: str
    delete: dict
    reply: str
    last_answer: str
    pending_id: str
    delete_prompt: str
    plan_failed: bool
    history: list[str]
    rounds: int
    more: bool
    empty_retried: bool
    queries: list[str]
    results: list[dict]
    feedback: list[dict]
    corrections: int
    answer: str
    outcome: str
