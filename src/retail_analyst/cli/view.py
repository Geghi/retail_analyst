import sys
from collections.abc import Callable
from contextlib import nullcontext
from datetime import datetime

from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from retail_analyst import observability

from .tables import INLINE_ROWS, format_value, is_number, render_table

GREETING = "Chatting as {user}. Type /trace, /reports, or exit."
COMMANDS = (
    ("/trace", "steps of the last answer"),
    ("/reports", "your saved reports"),
    ("/export", "save the tables of the last answer as CSV"),
    ("exit", "leave the chat"),
)
SKIPPED_DETAILS = {"ts", "trace_id", "user_id", "event", "ok", "duration_ms", "sql", "error"}


class PlainView:
    """Simple text output: used when not in a terminal, and by the tests."""

    def __init__(self, write: Callable[[str], None] = print):
        self.write = write

    def greeting(self, user: str) -> None:
        self.write(GREETING.format(user=user))

    def thinking(self):
        return nullcontext()

    def answer(self, reply) -> None:
        self.write(reply.text)
        for rows in reply.tables:
            self.write(render_table(rows))

    def notice(self, text: str) -> None:
        self.write(text)

    def trace(self, events: list[dict]) -> None:
        self.write(observability.format_trace(events))

    def reports(self, saved: list[tuple[str, object]]) -> None:
        self.write("\n".join(f"- {title} ({saved_on:%Y-%m-%d})" for title, saved_on in saved))


class RichView:
    """Colored terminal output: markdown answers, aligned tables, highlighted SQL."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def read(self, prompt: str) -> str:
        return self.console.input("[bold cyan]you>[/] ")

    def greeting(self, user: str) -> None:
        body = Text()
        body.append("Signed in as ")
        body.append(user, style="bold cyan")
        for command, meaning in COMMANDS:
            body.append(f"\n  {command:<9}", style="bold")
            body.append(meaning, style="dim")
        self.console.print(Panel(body, title="Retail Analyst", border_style="cyan", expand=False))

    def thinking(self):
        return self.console.status("[dim]Thinking...[/]", spinner="dots")

    def answer(self, reply) -> None:
        self.console.print()
        self.console.print(self._body(reply))
        for rows in reply.tables:
            self.console.print()
            self.console.print(self._table(rows))
        self.console.print()

    def _body(self, reply):
        if reply.kind == "error":
            return Text(f"x {reply.text}", style="bold red")
        if reply.kind == "refusal":
            return Text(reply.text, style="yellow")
        if reply.kind == "needs_confirmation":
            return Panel(Text(reply.text), title="Please confirm", border_style="yellow")
        return Markdown(reply.text)

    def _table(self, rows: list[dict]):
        columns = list(rows[0])
        table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", pad_edge=False)
        for name in columns:
            numeric = any(is_number(row.get(name)) for row in rows)
            table.add_column(name, justify="right" if numeric else "left")
        for row in rows[:INLINE_ROWS]:
            table.add_row(*(format_value(row.get(name)) for name in columns))
        hidden = len(rows) - INLINE_ROWS
        if hidden <= 0:
            return table
        note = Text(f"... {hidden} more rows (/export saves them all)", style="dim")
        return Group(table, note)

    def notice(self, text: str) -> None:
        self.console.print(Text(text, style="dim"))

    def trace(self, events: list[dict]) -> None:
        origin = _parse(events[0].get("ts")) if events else None
        table = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False)
        for name in ("time", "step", "status", "ms", "details"):
            table.add_column(name)
        sqls = []
        for event in events:
            table.add_row(
                _offset(event, origin),
                Text(str(event.get("event")), "bold"),
                _status(event),
                str(event.get("duration_ms", "")),
                Text(_details(event), "dim", overflow="ellipsis", no_wrap=True),
            )
            if event.get("sql"):
                sqls.append(Syntax(event["sql"], "sql", theme="ansi_dark", word_wrap=True))
        self.console.print(Group(table, *sqls))

    def reports(self, saved: list[tuple[str, object]]) -> None:
        table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", pad_edge=False)
        table.add_column("report")
        table.add_column("saved", style="dim")
        for title, saved_on in saved:
            table.add_row(title, f"{saved_on:%Y-%m-%d}")
        self.console.print(table)


def _status(event: dict) -> Text:
    if "ok" not in event:
        return Text("")
    if event["ok"] is False:
        return Text(f"x {event.get('error', 'failed')}", "red")
    return Text("ok", "green")


def _details(event: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in event.items() if k not in SKIPPED_DETAILS)


def _parse(value) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _offset(event: dict, origin: datetime | None) -> str:
    moment = _parse(event.get("ts"))
    if moment is None or origin is None:
        return ""
    return f"+{(moment - origin).total_seconds():.1f}s"


def choose_view(write: Callable[[str], None] = print):
    """A real terminal gets colors; a pipe, a test or a custom writer gets plain text."""
    if write is print and sys.stdout.isatty():
        return RichView()
    return PlainView(write)
