from .trio import Trio

INTRO = (
    "Past analyses follow as guidance on approach, table usage and report style. "
    "They are examples, not text to copy: write new SQL and a new report for the actual question."
)


def format_trio(trio: Trio) -> str:
    queries = "\n\n".join(f"SQL:\n{query.strip()}" for query in trio.queries)
    return f"Question: {trio.question}\n\n{queries}\n\nAnalyst report:\n{trio.report.strip()}"


def format_for_prompt(trios: list[Trio]) -> str:
    blocks = [f"Example {number}\n{format_trio(trio)}" for number, trio in enumerate(trios, 1)]
    return "\n\n---\n\n".join([INTRO, *blocks])
