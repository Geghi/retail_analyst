import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import resolve_log_path
from .scrub import scrub

MESSAGE_LIMIT = 200


class Turn:
    def __init__(self, user_id: str, path: Path) -> None:
        self.trace_id = uuid.uuid4().hex[:12]
        self._user_id = user_id
        self._path = path
        self._started = time.perf_counter()

    def event(self, name: str, **fields: Any) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "trace_id": self.trace_id,
            "user_id": self._user_id,
            "event": name,
            **fields,
        }
        try:
            line = json.dumps(scrub(record))
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            return

    @contextmanager
    def step(self, name: str, **fields: Any) -> Iterator[None]:
        began = time.perf_counter()
        try:
            yield
        except Exception as exc:
            self.event(
                name,
                ok=False,
                duration_ms=_elapsed_ms(began),
                error=type(exc).__name__,
                message=str(exc)[:MESSAGE_LIMIT],
                **fields,
            )
            raise
        self.event(name, ok=True, duration_ms=_elapsed_ms(began), **fields)

    def finish(self, outcome: str, **fields: Any) -> None:
        self.event(
            "turn_finished",
            outcome=outcome,
            duration_ms=_elapsed_ms(self._started),
            **fields,
        )


def _elapsed_ms(began: float) -> float:
    return round((time.perf_counter() - began) * 1000, 3)


def start_turn(user_id: str, question: str, log_path: Path | None = None) -> Turn:
    turn = Turn(user_id, resolve_log_path(log_path))
    turn.event("turn_started", question=question)
    return turn


def verbose() -> bool:
    return os.environ.get("TRACE_VERBOSE") == "1"
