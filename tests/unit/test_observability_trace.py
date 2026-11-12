import json

import pytest

from retail_analyst.observability import format_trace, read_trace, start_turn, summarize


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_events_of_one_turn_share_trace_id_and_keep_order(tmp_path):
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "revenue?", log_path=log)
    turn.event("sql_generated", sql="SELECT 1")
    turn.finish("answered")
    events = lines(log)
    assert [e["event"] for e in events] == ["turn_started", "sql_generated", "turn_finished"]
    assert {e["trace_id"] for e in events} == {turn.trace_id}
    assert {e["user_id"] for e in events} == {"alice"}
    assert events[1]["sql"] == "SELECT 1"
    assert events[2]["outcome"] == "answered"
    assert events[2]["duration_ms"] >= 0
    assert events[0]["ts"].endswith("+00:00")


def test_step_records_duration_and_ok(tmp_path):
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "q", log_path=log)
    with turn.step("bq_query", rows=3):
        pass
    step = lines(log)[-1]
    assert step["event"] == "bq_query"
    assert step["ok"] is True
    assert step["rows"] == 3
    assert step["duration_ms"] >= 0


def test_failing_step_records_error_and_reraises(tmp_path):
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "q", log_path=log)
    with pytest.raises(ValueError), turn.step("bq_query"):
        raise ValueError("bad column")
    step = lines(log)[-1]
    assert step["ok"] is False
    assert step["error"] == "ValueError"
    assert step["message"] == "bad column"


def test_api_key_never_reaches_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sekret-123")
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "my key sekret-123", log_path=log)
    turn.event("llm", nested={"a": ["x sekret-123 y"]}, other=1)
    with pytest.raises(RuntimeError), turn.step("s"):
        raise RuntimeError("url?key=sekret-123")
    text = log.read_text()
    assert "sekret-123" not in text
    assert "***" in text


def test_non_serializable_values_are_logged_via_repr(tmp_path):
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "q", log_path=log)
    turn.event("odd", value={1, 2})
    assert lines(log)[-1]["value"] == repr({1, 2})


def test_default_path_uses_log_dir_at_call_time(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "deep" / "logs"))
    turn = start_turn("alice", "q")
    turn.finish("answered")
    assert len(read_trace(turn.trace_id)) == 2
    assert (tmp_path / "deep" / "logs" / "agent.jsonl").exists()


def test_read_trace_without_id_returns_latest_turn_only(tmp_path):
    log = tmp_path / "agent.jsonl"
    first = start_turn("alice", "one", log_path=log)
    first.finish("answered")
    second = start_turn("bob", "two", log_path=log)
    second.finish("refused")
    latest = read_trace(log_path=log)
    assert {e["trace_id"] for e in latest} == {second.trace_id}
    assert len(latest) == 2
    assert len(read_trace(first.trace_id, log_path=log)) == 2


def test_corrupt_lines_are_skipped(tmp_path):
    log = tmp_path / "agent.jsonl"
    turn = start_turn("alice", "q", log_path=log)
    with log.open("a") as f:
        f.write("{not json\n\n")
    turn.finish("answered")
    assert [e["event"] for e in read_trace(log_path=log)] == ["turn_started", "turn_finished"]
    assert summarize(log)["turns"] == 1


def test_missing_log_gives_empty_results(tmp_path):
    log = tmp_path / "none.jsonl"
    assert read_trace(log_path=log) == []
    assert summarize(log)["turns"] == 0
    assert summarize(log)["failure_rate"] == 0.0


def test_log_write_failure_is_swallowed(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    turn = start_turn("alice", "q", log_path=blocker / "sub" / "agent.jsonl")
    turn.event("e")
    with turn.step("s"):
        pass
    turn.finish("answered")


def test_format_trace_shows_offsets_status_duration_and_sql():
    events = [
        {"ts": "2026-01-01T00:00:00+00:00", "event": "turn_started", "question": "q"},
        {
            "ts": "2026-01-01T00:00:01.500000+00:00",
            "event": "bq_query",
            "ok": False,
            "duration_ms": 12.5,
            "error": "BadRequest",
            "sql": "SELECT 1",
        },
    ]
    out = format_trace(events).splitlines()
    assert len(out) == 2
    assert "+1.500s" in out[1]
    assert "bq_query" in out[1]
    assert "ERROR BadRequest" in out[1]
    assert "12.5ms" in out[1]
    assert "SELECT 1" in out[1]
    assert format_trace([]) == ""
