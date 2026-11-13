from collections.abc import Callable
from pathlib import Path

import psycopg

from retail_analyst import observability, reports
from retail_analyst.agent import Agent

from .tables import export_tables
from .view import PlainView

EXIT_WORDS = {"exit", "quit"}
PROMPT = "you> "
REPORTS_DOWN = "Saved reports are temporarily unavailable. Please try again in a moment."
NO_REPORTS = "No saved reports."
NOTHING_TO_EXPORT = "Nothing to export yet. Ask a question first."
NO_TRACE = "No questions asked yet, so there is no trace to show."


def run_chat(
    agent: Agent,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
    export_dir: Path = Path("exports"),
    view=None,
):
    view = view or PlainView(write)
    last_trace_id = None
    last_tables: tuple = ()
    while True:
        try:
            line = read(PROMPT).strip()
        except EOFError:
            return
        if line.lower() in EXIT_WORDS:
            return
        if line == "/trace":
            show_trace(view, agent, last_trace_id)
        elif line == "/reports":
            show_reports(view, agent)
        elif line == "/export":
            view.notice(export_last(agent, last_tables, last_trace_id, export_dir))
        elif line:
            with view.thinking():
                reply = agent.respond(line)
            last_trace_id, last_tables = reply.trace_id, reply.tables
            view.answer(reply)


def export_last(agent: Agent, tables: tuple, trace_id: str | None, directory: Path) -> str:
    if not tables:
        return NOTHING_TO_EXPORT
    saved = export_tables(tables, directory, f"{agent.user_id}-{trace_id[:8]}")
    return "Saved:\n" + "\n".join(f"  {path}" for path in saved)


def show_trace(view, agent: Agent, trace_id: str | None) -> None:
    if trace_id is None:
        view.notice(NO_TRACE)
        return
    view.trace(observability.read_trace(trace_id, agent.deps.log_path))


def show_reports(view, agent: Agent) -> None:
    try:
        saved = reports.list_reports(agent.deps.conn, agent.user_id)
    except psycopg.Error:
        view.notice(REPORTS_DOWN)
        return
    if not saved:
        view.notice(NO_REPORTS)
        return
    view.reports([(report.title, report.created_at) for report in saved])
