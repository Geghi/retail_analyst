import json
import re

FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class ReplyFormatError(ValueError):
    pass


def parse_json_reply(text: str) -> dict:
    try:
        reply = json.loads(FENCE.sub("", text.strip()))
    except json.JSONDecodeError as error:
        raise ReplyFormatError("not JSON") from error
    if not isinstance(reply, dict):
        raise ReplyFormatError("not an object")
    return reply


BAD_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')
UNREADABLE = "I could not format the answer. Please ask again or rephrase the question."


def readable_answer(text: str) -> tuple[str, list]:
    """Turn the analyst's reply into text for the user and its follow-up queries.

    Plain prose is shown as is. Anything that looks like JSON but cannot be read raises
    ReplyFormatError, so it is never shown raw.
    """
    stripped = FENCE.sub("", text.strip())
    if not stripped.startswith("{"):
        return text, []
    try:
        reply = json.loads(BAD_ESCAPE.sub(r"\\\\", stripped))
    except json.JSONDecodeError as error:
        raise ReplyFormatError("not JSON") from error
    if not isinstance(reply, dict) or "answer" not in reply:
        raise ReplyFormatError("no answer")
    return compose_text(reply), list(reply.get("follow_up_queries") or [])


def compose_text(reply: dict) -> str:
    parts = [str(reply["answer"])]
    for key in ("summary", "findings", "text"):
        extra = str(reply.get(key) or "")
        if extra and extra not in parts[0]:
            parts.append(extra)
    actions = reply.get("action_items") or []
    if actions:
        parts.append("\n".join(f"- {item}" for item in actions))
    return "\n\n".join(part for part in parts if part)
