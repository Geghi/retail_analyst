import os

import pytest
from dotenv import find_dotenv, load_dotenv

from retail_analyst import settings
from retail_analyst.agent import Agent, AgentDeps
from retail_analyst.storage import connect, create_tables

REQUIRED = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_FALLBACK_MODEL",
    "GCP_PROJECT_ID",
    "DATABASE_URL",
)


@pytest.fixture(scope="session", autouse=True)
def live_setup():
    """Runs only when acceptance tests are selected, so the env file is never loaded otherwise."""
    load_dotenv(find_dotenv(usecwd=True))
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        pytest.skip(f"live setup incomplete: {missing}")


@pytest.fixture(scope="session")
def conn(live_setup):
    connection = connect(os.environ["DATABASE_URL"])
    create_tables(connection)
    yield connection
    connection.close()


@pytest.fixture
def make_agent(conn, tmp_path):
    def build(user="alice", **overrides):
        deps = AgentDeps(conn=conn, log_path=tmp_path / "trace.jsonl", **overrides)
        return Agent(user, deps)

    return build


@pytest.fixture
def allowed_categories():
    return settings.load_scope("alice").allowed_categories
