import os
from typing import Any

MASK = "***"


def scrub(value: Any) -> Any:
    secret = os.environ.get("GEMINI_API_KEY")
    return _scrub(value, secret)


def _scrub(value: Any, secret: str | None) -> Any:
    if isinstance(value, str):
        return value.replace(secret, MASK) if secret else value
    if isinstance(value, dict):
        return {str(k): _scrub(v, secret) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub(v, secret) for v in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    return _scrub(repr(value), secret)
