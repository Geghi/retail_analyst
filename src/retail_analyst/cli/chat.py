from collections.abc import Callable
from pathlib import Path

import psycopg

from retail_analyst import observability, reports
from retail_analyst.agent import Agent

from .tables import export_tables, render_table

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
):
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
            write(show_trace(agent, last_trace_id))
        elif line == "/reports":
            write(show_reports(agent))
        elif line == "/export":
            write(export_last(agent, last_tables, last_trace_id, export_dir))
        elif line:
            reply = agent.respond(line)
            last_trace_id, last_tables = reply.trace_id, reply.tables
            write(reply.text)
            for table in reply.tables:
                write(render_table(table))


def export_last(agent: Agent, tables: tuple, trace_id: str | None, directory: Path) -> str:
    if not tables:
        return NOTHING_TO_EXPORT
    saved = export_tables(tables, directory, f"{agent.user_id}-{trace_id[:8]}")
    return "Saved:\n" + "\n".join(f"  {path}" for path in saved)


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
