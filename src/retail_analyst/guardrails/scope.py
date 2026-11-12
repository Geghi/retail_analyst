from dataclasses import dataclass


@dataclass(frozen=True)
class UserScope:
    user_id: str
    allowed_categories: frozenset[str]
