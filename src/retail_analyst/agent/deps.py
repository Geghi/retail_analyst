from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from retail_analyst import knowledge, llm, settings, warehouse


@dataclass
class AgentDeps:
    generate: Callable[..., str] = llm.generate
    run_query: Callable[..., Any] = warehouse.run_query
    load_scope: Callable[[str], Any] = settings.load_scope
    load_persona: Callable[[], str] = settings.load_persona
    find_similar: Callable[[str], list] = knowledge.find_similar
    today: Callable[[], date] = date.today
    log_path: Path | None = None
    conn: Any = None
    retry_interval: float = 1.0
    extra: dict = field(default_factory=dict)
