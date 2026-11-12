import csv

from agent_support import (
    REVENUE_SQL,
    FakeWarehouse,
    ScriptedLlm,
    analyst_reply,
    make_deps,
    plan_reply,
    rows_result,
)
from retail_analyst.agent import Agent
from retail_analyst.cli import render_table, run_chat

ROWS = [
    {"category": "Jeans", "revenue": 40931.91, "orders": 418, "return_rate": 0.0881},
    {"category": "Sweaters", "revenue": 29279.78, "orders": 380, "return_rate": 0.1128},
]


def test_a_table_is_aligned_with_a_header_and_readable_numbers():
    assert render_table(ROWS).splitlines() == [
        "category  revenue    orders  return_rate",
        "--------  ---------  ------  -----------",
        "Jeans     40,931.91     418       0.0881",
        "Sweaters  29,279.78     380       0.1128",
    ]


def test_a_missing_value_is_shown_as_a_dash():
    assert render_table([{"brand": "Levi", "revenue": None}]).splitlines()[-1] == "Levi   -"


def test_a_long_table_shows_the_first_ten_rows_and_how_many_more_there_are():
    rows = [{"n": i} for i in range(25)]

    lines = render_table(rows).splitlines()

    assert len(lines) == 2 + 10 + 1
    assert lines[2].strip() == "0" and lines[11].strip() == "9"
    assert lines[-1] == "... 15 more rows (/export saves them all)"


def chat(agent, *lines, export_dir):
    typed = iter(lines)
    shown = []

    def read(prompt):
        try:
            return next(typed)
        except StopIteration:
            raise EOFError from None

    run_chat(agent, read=read, write=shown.append, export_dir=export_dir)
    return shown


def revenue_agent(tmp_path, rows):
    llm = ScriptedLlm([plan_reply(REVENUE_SQL), analyst_reply("Jeans lead.")])
    return Agent("alice", make_deps(llm, FakeWarehouse([rows_result(rows)]), tmp_path))


def test_the_answer_is_followed_by_its_table(tmp_path):
    shown = chat(revenue_agent(tmp_path, ROWS), "Revenue?", export_dir=tmp_path / "exports")

    assert shown[0] == "Jeans lead."
    assert "Sweaters  29,279.78" in shown[1]


def test_export_saves_every_row_of_the_last_answer_as_a_csv_file(tmp_path):
    rows = [{"n": i, "label": f"row {i}"} for i in range(25)]
    exports = tmp_path / "exports"

    shown = chat(revenue_agent(tmp_path, rows), "Revenue?", "/export", export_dir=exports)

    (saved,) = list(exports.glob("*.csv"))
    assert str(saved) in shown[-1]
    with saved.open(newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == 25
    assert written[24] == {"n": "24", "label": "row 24"}


def test_export_before_any_answer_says_there_is_nothing_to_save(tmp_path):
    shown = chat(revenue_agent(tmp_path, ROWS), "/export", export_dir=tmp_path / "exports")

    assert shown == ["Nothing to export yet. Ask a question first."]
    assert not (tmp_path / "exports").exists()
