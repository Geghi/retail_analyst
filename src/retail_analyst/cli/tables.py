import csv
from pathlib import Path

INLINE_ROWS = 10


def is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def format_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 1 else f"{value:,.2f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def render_table(rows: list[dict], max_rows: int = INLINE_ROWS) -> str:
    columns = list(rows[0])
    shown = rows[:max_rows]
    cells = [[format_value(row.get(name)) for name in columns] for row in shown]
    widths = [max(len(name), *(len(line[i]) for line in cells)) for i, name in enumerate(columns)]

    def line(parts: list[str], numeric: list[bool]) -> str:
        padded = [
            p.rjust(w) if n else p.ljust(w) for p, w, n in zip(parts, widths, numeric, strict=True)
        ]
        return "  ".join(padded).rstrip()

    text = [
        line(columns, [False] * len(columns)),
        line(["-" * w for w in widths], [False] * len(columns)),
    ]
    for row, parts in zip(shown, cells, strict=True):
        text.append(line(parts, [is_number(row.get(name)) for name in columns]))
    if len(rows) > max_rows:
        text.append(f"... {len(rows) - max_rows} more rows (/export saves them all)")
    return "\n".join(text)


def export_tables(tables: tuple, directory: Path, prefix: str) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    saved = []
    for number, rows in enumerate(tables, start=1):
        path = directory / f"{prefix}-{number}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        saved.append(path)
    return saved
