from collections.abc import Callable

import psycopg

from retail_analyst import observability, reports
from retail_analyst.agent import Agent

EXIT_WORDS = {"exit", "quit"}
PROMPT = "you> "
REPORTS_DOWN = "Saved reports are temporarily unavailable. Please try again in a moment."
NO_REPORTS = "No saved reports."
NO_TRACE = "No questions asked yet, so there is no trace to show."


def run_chat(
    agent: Agent,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
):
    last_trace_id = None
    while True:
        try:
            line = read(PROMPT).strip()
        except EOFError:
            return
        if line.lower() in EXIT_WORDS:
            return
        if line == "/trace":
            write(show_trace(agent, last_trace_id))
        elif line == "/reports":
            write(show_reports(agent))
        elif line:
            reply = agent.respond(line)
            last_trace_id = reply.trace_id
            write(reply.text)


def show_trace(agent: Agent, trace_id: str | None) -> str:
    if trace_id is None:
        return NO_TRACE
    return observability.format_trace(observability.read_trace(trace_id, agent.deps.log_path))


def show_reports(agent: Agent) -> str:
    try:
        saved = reports.list_reports(agent.deps.conn, agent.user_id)
    except psycopg.Error:
        return REPORTS_DOWN
    if not saved:
        return NO_REPORTS
    return "\n".join(f"- {report.title} ({report.created_at:%Y-%m-%d})" for report in saved)
