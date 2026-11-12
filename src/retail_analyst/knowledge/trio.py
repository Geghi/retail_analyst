import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_DIRECTORY = Path(__file__).resolve().parents[3] / "golden"


@dataclass(frozen=True)
class Trio:
    id: str
    question: str
    queries: list[str]
    report: str


def parse_trio(path: Path) -> Trio:
    try:
        data = yaml.safe_load(path.read_text())
        queries = data["queries"]
        valid = all(isinstance(data[key], str) for key in ("id", "question", "report"))
        valid = valid and isinstance(queries, list) and all(isinstance(q, str) for q in queries)
        if not valid:
            raise TypeError("fields have the wrong type")
        return Trio(data["id"], data["question"], list(queries), data["report"])
    except (yaml.YAMLError, KeyError, TypeError) as error:
        raise ValueError(f"Malformed golden file {path.name}: {error}") from error


def load_trios(directory: Path | None = None) -> list[Trio]:
    folder = directory or Path(os.environ.get("GOLDEN_DIR") or DEFAULT_DIRECTORY)
    return [parse_trio(path) for path in sorted(folder.glob("*.yaml"))]
