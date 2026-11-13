import io
from datetime import date

from rich.console import Console

from retail_analyst.agent import Reply
from retail_analyst.cli import PlainView, RichView, choose_view

ROWS = [
    {"category": "Jeans", "revenue": 40931.91, "orders": 418},
    {"category": "Sweaters", "revenue": 29279.78, "orders": 380},
]
TRACE = [
    {"ts": "2026-11-12T10:00:00+00:00", "event": "turn_started", "question": "revenue?"},
    {
        "ts": "2026-11-12T10:00:01+00:00",
        "event": "query",
        "ok": True,
        "rows": 2,
        "sql": "SELECT category, SUM(sale_price) FROM order_items GROUP BY category",
    },
    {"ts": "2026-11-12T10:00:02+00:00", "event": "plan", "ok": False, "error": "LlmUnavailable"},
]


def rich_view(color=False):
    buffer = io.StringIO()
    console = Console(
        file=buffer, width=90, force_terminal=color, color_system="standard" if color else None
    )
    return RichView(console), buffer


def reply(kind="answer", text="Jeans lead.", tables=()):
    return Reply(kind=kind, text=text, trace_id="t1", tables=tables)


def test_the_answer_is_rendered_as_markdown_not_as_raw_symbols():
    view, out = rich_view()

    view.answer(reply(text="### Summary\n- Jeans lead\n- Sweaters follow"))

    shown = out.getvalue()
    assert "Summary" in shown and "Jeans lead" in shown
    assert "###" not in shown


def test_a_table_shows_headers_thousands_separators_and_how_many_rows_are_hidden():
    view, out = rich_view()
    rows = [{"n": i, "revenue": 1234.5} for i in range(25)]

    view.answer(reply(tables=(rows,)))

    shown = out.getvalue()
    assert "revenue" in shown and "1,234.50" in shown
    assert "15 more rows" in shown and "/export" in shown


def test_an_error_and_a_refusal_are_colored_differently_from_an_answer():
    view, out = rich_view(color=True)
    view.answer(reply(kind="answer", text="plain answer"))
    plain = out.getvalue()
    view.answer(reply(kind="error", text="The AI service is down."))
    view.answer(reply(kind="refusal", text="I cannot share personal data."))

    shown = out.getvalue()
    assert "The AI service is down." in shown and "I cannot share personal data." in shown
    assert shown.count("\x1b[") > plain.count("\x1b[")


def test_a_confirmation_request_is_set_apart_and_keeps_the_yes_no_question():
    view, out = rich_view()

    view.answer(
        reply(
            kind="needs_confirmation",
            text="These reports will be deleted:\n- A\nDo you confirm? (yes / no)",
        )
    )

    assert "Do you confirm? (yes / no)" in out.getvalue()


def test_the_trace_lists_each_step_with_its_sql_and_marks_failures():
    view, out = rich_view()

    view.trace(TRACE)

    shown = out.getvalue()
    assert "turn_started" in shown and "query" in shown and "plan" in shown
    assert "SELECT category" in shown
    assert "LlmUnavailable" in shown


def test_saved_reports_are_listed_with_their_date():
    view, out = rich_view()

    view.reports([("October revenue", date(2026, 11, 12))])

    assert "October revenue" in out.getvalue() and "2026-11-12" in out.getvalue()


def test_the_greeting_names_the_user_and_lists_the_commands():
    view, out = rich_view()

    view.greeting("alice")

    shown = out.getvalue()
    assert "alice" in shown
    assert "/trace" in shown and "/reports" in shown and "/export" in shown


def test_the_plain_view_keeps_the_simple_text_output():
    shown = []
    view = PlainView(shown.append)

    view.greeting("alice")
    view.answer(reply(text="Jeans lead.", tables=(ROWS,)))
    view.reports([("October revenue", date(2026, 11, 12))])

    assert shown[0] == "Chatting as alice. Type /trace, /reports, or exit."
    assert shown[1] == "Jeans lead."
    assert "Sweaters  29,279.78" in shown[2]
    assert shown[3] == "- October revenue (2026-11-12)"


def test_a_terminal_gets_the_rich_view_and_a_pipe_or_custom_writer_gets_plain_text(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert isinstance(choose_view(print), RichView)
    assert isinstance(choose_view([].append), PlainView)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert isinstance(choose_view(print), PlainView)
