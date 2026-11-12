import os
from pathlib import Path

import yaml

from retail_analyst.guardrails import UserScope

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class UnknownUser(Exception):
    pass


def config_dir() -> Path:
    return Path(os.environ.get("CONFIG_DIR") or DEFAULT_CONFIG_DIR)


def read_users(path: Path | None) -> dict:
    path = path or config_dir() / "users.yaml"
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot read users file {path.name}: {type(error).__name__}") from None
    users = data.get("users") if isinstance(data, dict) else None
    if not isinstance(users, dict) or not users:
        raise ValueError(f"Users file {path.name} must contain a non-empty 'users' mapping")
    for user_id, entry in users.items():
        categories = entry.get("categories") if isinstance(entry, dict) else None
        if not isinstance(categories, list) or not categories:
            raise ValueError(f"Users file {path.name}: user '{user_id}' needs a 'categories' list")
    return users


def load_scope(user_id: str, path: Path | None = None) -> UserScope:
    users = read_users(path)
    if user_id not in users:
        raise UnknownUser(f"Unknown user '{user_id}'")
    return UserScope(user_id, frozenset(users[user_id]["categories"]))


def list_users(path: Path | None = None) -> list[str]:
    return list(read_users(path))


def load_persona(path: Path | None = None) -> str:
    return (path or config_dir() / "persona.md").read_text()
