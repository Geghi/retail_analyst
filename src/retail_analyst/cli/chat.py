from collections.abc import Callable
from pathlib import Path

import psycopg

from retail_analyst import observability, reports
from retail_analyst.agent import Agent

from .tables import export_tables
from .view import PlainView

EXIT_WORDS = {"exit", "quit"}
PROMPT = "you> "
OPEN_PROMPT = "report number (Enter to go back)> "
REPORTS_DOWN = "Saved reports are temporarily unavailable. Please try again in a moment."
NO_REPORTS = "No saved reports."
NOTHING_TO_EXPORT = "Nothing to export yet. Ask a question first."
EXPORT_FAILED = "The tables could not be saved to {directory}. Check that the folder is writable."
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
    typed_ahead = None
    while True:
        try:
            line = typed_ahead if typed_ahead is not None else read(PROMPT).strip()
        except EOFError:
            return
        typed_ahead = None
        if line.lower() in EXIT_WORDS:
            return
        if line == "/trace":
            show_trace(view, agent, last_trace_id)
        elif line == "/reports":
            typed_ahead = show_reports(view, agent, read)
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
    try:
        saved = export_tables(tables, directory, f"{agent.user_id}-{trace_id[:8]}")
    except OSError:
        return EXPORT_FAILED.format(directory=directory)
    return "Saved:\n" + "\n".join(f"  {path}" for path in saved)


def show_trace(view, agent: Agent, trace_id: str | None) -> None:
    if trace_id is None:
        view.notice(NO_TRACE)
        return
    view.trace(observability.read_trace(trace_id, agent.deps.log_path))


def show_reports(view, agent: Agent, read: Callable[[str], str]) -> str | None:
    """List the reports and open them by number; returns a line that was not a number."""
    try:
        saved = reports.list_reports(agent.deps.conn, agent.user_id)
    except psycopg.Error:
        view.notice(REPORTS_DOWN)
        return
    if not saved:
        view.notice(NO_REPORTS)
        return
    view.reports([(report.title, report.created_at) for report in saved])
    while True:
        try:
            choice = read(OPEN_PROMPT).strip()
        except EOFError:
            return None
        if not choice.isdigit():
            return choice or None
        number = int(choice)
        if 1 <= number <= len(saved):
            chosen = saved[number - 1]
            view.report(chosen.title, chosen.created_at, chosen.body)
        else:
            view.notice(f"There is no report number {number}.")
