import os
from pathlib import Path


def resolve_log_path(log_path: Path | None) -> Path:
    if log_path is not None:
        return log_path
    return Path(os.environ.get("LOG_DIR", "logs")) / "agent.jsonl"
