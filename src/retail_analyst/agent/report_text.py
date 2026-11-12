import re

NOTHING_TO_SAVE = "There is no report to save yet. Ask me for an analysis first."
NO_MATCH = "No saved report matches that request, so nothing will be deleted."
CANCELLED = "Understood, I did not delete anything."
EXPIRED = "That deletion request is no longer valid. Please ask again."
YES = {"yes", "y", "confirm", "ok", "okay", "sure", "si", "sì"}
NO = {"no", "n", "cancel", "stop", "abort"}


def report_title(question: str) -> str:
    return " ".join(question.split())[:80] or "Report"


def normalize_answer(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text).strip().lower()


def deletion_prompt(titles: list[str]) -> str:
    listed = "\n".join(f"- {title}" for title in titles)
    return f"These saved reports will be deleted:\n{listed}\nDo you confirm? (yes / no)"
