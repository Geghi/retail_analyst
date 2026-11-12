import os

import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id uuid PRIMARY KEY,
    user_id text NOT NULL,
    title text NOT NULL,
    body text NOT NULL,
    conversation_id text NOT NULL,
    created_at timestamptz NOT NULL,
    deleted_at timestamptz
);
CREATE INDEX IF NOT EXISTS reports_user_id_idx ON reports (user_id);
CREATE TABLE IF NOT EXISTS pending_deletions (
    id uuid PRIMARY KEY,
    user_id text NOT NULL,
    report_ids uuid[] NOT NULL,
    created_at timestamptz NOT NULL
);
"""


def connect(database_url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(database_url or os.environ["DATABASE_URL"], autocommit=True)


def create_tables(conn: psycopg.Connection) -> None:
    conn.execute("SELECT pg_advisory_lock(7301)")
    try:
        conn.execute(SCHEMA)
    finally:
        conn.execute("SELECT pg_advisory_unlock(7301)")


__all__ = ["connect", "create_tables"]
