import re

from .pii import BLOCKED_COLUMNS

REDACTED = "[REDACTED]"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\w)\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?!\w)")


def mask_value(value):
    if not isinstance(value, str):
        return value
    return PHONE.sub(REDACTED, EMAIL.sub(REDACTED, value))


def mask_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            key: REDACTED if key.lower() in BLOCKED_COLUMNS else mask_value(value)
            for key, value in row.items()
        }
        for row in rows
    ]
