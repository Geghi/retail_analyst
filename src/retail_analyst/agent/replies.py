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
