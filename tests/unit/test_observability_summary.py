import json
import subprocess
import sys

from retail_analyst.observability import summarize


def build_log(path):
    def turn(trace, outcome, steps, extra=()):
        rows = [{"trace_id": trace, "event": "turn_started"}]
        rows += [
            {"trace_id": trace, "event": n, "ok": ok, "duration_ms": d, **e}
            for n, ok, d, e in steps
        ]
        rows += [{"trace_id": trace, "event": name} for name in extra]
        rows.append({"trace_id": trace, "event": "turn_finished", "outcome": outcome})
        return rows

    rows = (
        turn("a", "answered", [("bq", True, 10, {}), ("bq", True, 20, {})], ["retry"])
        + turn("b", "answered", [("bq", True, 30, {}), ("llm", True, 5, {})])
        + turn("c", "refused", [])
        + turn("d", "error", [("bq", False, 40, {"error": "BadRequest"})], ["retry", "retry"])
    )
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\nbroken{\n")


def test_summarize_counts_and_percentiles(tmp_path):
    log = tmp_path / "agent.jsonl"
    build_log(log)
    s = summarize(log)
    assert s["turns"] == 4
    assert s["outcomes"] == {"answered": 2, "refused": 1, "error": 1}
    assert s["failure_rate"] == 0.25
    assert s["refusals"] == 1
    assert s["retries"] == 3
    assert s["steps"]["bq"] == {"count": 4, "p50": 20, "p95": 40}
    assert s["steps"]["llm"] == {"count": 1, "p50": 5, "p95": 5}
    assert s["errors_by_type"] == {"BadRequest": 1}


def test_module_main_prints_a_table(tmp_path):
    log = tmp_path / "logs" / "agent.jsonl"
    log.parent.mkdir()
    build_log(log)
    import os

    env = {**os.environ, "LOG_DIR": str(log.parent), "PYTHONPATH": "src"}
    out = subprocess.run(
        [sys.executable, "-m", "retail_analyst.observability"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout
    assert "turns" in out and "bq" in out and "BadRequest" in out


def test_summarize_adds_up_token_usage_over_all_model_calls(tmp_path):
    log = tmp_path / "agent.jsonl"
    rows = [
        {"trace_id": "a", "event": "llm", "input_tokens": 100, "output_tokens": 20},
        {"trace_id": "a", "event": "llm", "input_tokens": 50, "output_tokens": 10},
        {"trace_id": "a", "event": "turn_finished", "outcome": "answered"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))

    result = summarize(log)

    assert result["tokens"] == {"calls": 2, "input": 150, "output": 30}


def test_the_summary_table_shows_model_calls_and_tokens():
    from retail_analyst.observability.__main__ import render

    summary = {
        "turns": 1,
        "failure_rate": 0.0,
        "refusals": 0,
        "retries": 0,
        "outcomes": {},
        "steps": {},
        "errors_by_type": {},
        "tokens": {"calls": 2, "input": 150, "output": 30},
    }

    table = render(summary)

    assert "model calls" in table and "2" in table
    assert "tokens in" in table and "150" in table
    assert "tokens out" in table and "30" in table
