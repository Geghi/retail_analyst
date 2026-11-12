import argparse
import os
from collections.abc import Callable, Mapping
from pathlib import Path

import psycopg

from retail_analyst import settings, storage
from retail_analyst.agent import Agent, AgentDeps

from .chat import run_chat

REQUIRED_ENV = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_FALLBACK_MODEL",
    "GCP_PROJECT_ID",
    "DATABASE_URL",
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="retail-analyst", description="Retail data-analysis chat")
    parser.add_argument("--user", required=True, help="user to chat as, e.g. alice")
    return parser.parse_args(argv)


def main(
    argv: list[str],
    env: Mapping[str, str] = os.environ,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> int:
    args = parse_args(argv)
    try:
        settings.load_scope(args.user)
    except settings.UnknownUser:
        write(f"Unknown user '{args.user}'. Valid users: {', '.join(settings.list_users())}.")
        return 2
    problem = missing_setup(env)
    if problem:
        write(problem)
        return 1
    try:
        conn = storage.connect(env["DATABASE_URL"])
        storage.create_tables(conn)
    except psycopg.Error:
        write("Cannot reach the reports database. Start it with: docker compose up -d db")
        return 1
    write(f"Chatting as {args.user}. Type /trace, /reports, or exit.")
    run_chat(Agent(args.user, AgentDeps(conn=conn)), read=read, write=write)
    return 0


def missing_setup(env: Mapping[str, str]) -> str | None:
    for name in REQUIRED_ENV:
        if not env.get(name):
            return f"{name} is not set. Copy .env.example to .env and fill it in."
    credentials = env.get("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials and not Path(credentials).is_file():
        return f"GOOGLE_APPLICATION_CREDENTIALS points to a file that does not exist: {credentials}"
    return None
