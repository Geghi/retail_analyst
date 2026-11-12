import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import resolve_log_path

BASE_KEYS = {"ts", "trace_id", "user_id", "event", "ok", "duration_ms", "error"}


def _load(log_path: Path | None) -> list[dict]:
    path = resolve_log_path(log_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    events = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            events.append(record)
    return events


def read_trace(trace_id: str | None = None, log_path: Path | None = None) -> list[dict]:
    events = _load(log_path)
    if trace_id is None and events:
        trace_id = events[-1].get("trace_id")
    return [e for e in events if e.get("trace_id") == trace_id]


def _offset(event: dict, origin: datetime | None) -> str:
    try:
        seconds = (datetime.fromisoformat(event["ts"]) - origin).total_seconds()
    except (KeyError, TypeError, ValueError):
        return "+?.???s"
    return f"+{seconds:.3f}s"


def _status(event: dict) -> str:
    if event.get("ok") is False:
        return f"ERROR {event.get('error', '')}".strip()
    return "ok" if event.get("ok") else ""


def format_trace(events: list[dict]) -> str:
    origin = None
    if events:
        try:
            origin = datetime.fromisoformat(events[0]["ts"])
        except (KeyError, TypeError, ValueError):
            origin = None
    rows = []
    for event in events:
        parts = [_offset(event, origin), str(event.get("event")), _status(event)]
        if "duration_ms" in event:
            parts.append(f"{event['duration_ms']}ms")
        parts += [f"{k}={v}" for k, v in event.items() if k not in BASE_KEYS]
        rows.append("  ".join(p for p in parts if p))
    return "\n".join(rows)


def _percentile(sorted_values: list[float], percent: int) -> float:
    return sorted_values[math.ceil(percent / 100 * len(sorted_values)) - 1]


def _token_totals(events: list[dict]) -> dict[str, float]:
    calls = [e for e in events if e.get("event") == "llm"]
    return {
        "calls": len(calls),
        "input": sum(e.get("input_tokens", 0) for e in calls),
        "output": sum(e.get("output_tokens", 0) for e in calls),
        "cost_usd": round(sum(e.get("cost_usd") or 0 for e in calls), 6),
    }


def summarize(log_path: Path | None = None) -> dict[str, Any]:
    events = _load(log_path)
    finished = [e for e in events if e.get("event") == "turn_finished"]
    outcomes = Counter(e.get("outcome") for e in finished)
    durations: dict[str, list[float]] = {}
    errors: Counter = Counter()
    for event in events:
        if "ok" in event and "duration_ms" in event:
            durations.setdefault(event["event"], []).append(event["duration_ms"])
        if event.get("ok") is False:
            errors[event.get("error", "unknown")] += 1
    steps = {
        name: {
            "count": len(values),
            "p50": _percentile(sorted(values), 50),
            "p95": _percentile(sorted(values), 95),
        }
        for name, values in durations.items()
    }
    turns = len(finished)
    return {
        "tokens": _token_totals(events),
        "turns": turns,
        "outcomes": dict(outcomes),
        "failure_rate": outcomes["error"] / turns if turns else 0.0,
        "refusals": outcomes["refused"],
        "retries": sum(1 for e in events if e.get("event") == "retry"),
        "steps": steps,
        "errors_by_type": dict(errors),
    }
