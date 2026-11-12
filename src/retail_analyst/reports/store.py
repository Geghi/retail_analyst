import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import class_row

from .errors import NotRestorable


@dataclass(frozen=True)
class Report:
    id: uuid.UUID
    user_id: str
    title: str
    body: str
    conversation_id: str
    created_at: datetime
    deleted_at: datetime | None


def utcnow() -> datetime:
    return datetime.now(UTC)


def save_report(
    conn: psycopg.Connection, user_id: str, title: str, body: str, conversation_id: str
) -> Report:
    with conn.cursor(row_factory=class_row(Report)) as cur:
        return cur.execute(
            "INSERT INTO reports (id, user_id, title, body, conversation_id, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
            (uuid.uuid4(), user_id, title, body, conversation_id, utcnow()),
        ).fetchone()


def list_reports(
    conn: psycopg.Connection, user_id: str, *, include_deleted: bool = False
) -> list[Report]:
    with conn.cursor(row_factory=class_row(Report)) as cur:
        return cur.execute(
            "SELECT * FROM reports WHERE user_id = %s"
            " AND (%s OR deleted_at IS NULL) ORDER BY created_at, id",
            (user_id, include_deleted),
        ).fetchall()


RESTORE_WINDOW = timedelta(days=30)


def restore_report(
    conn: psycopg.Connection, user_id: str, report_id: uuid.UUID, *, now: datetime | None = None
) -> None:
    now = now or utcnow()
    restored = conn.execute(
        "UPDATE reports SET deleted_at = NULL WHERE id = %s AND user_id = %s"
        " AND deleted_at IS NOT NULL AND deleted_at >= %s",
        (report_id, user_id, now - RESTORE_WINDOW),
    )
    if restored.rowcount == 0:
        raise NotRestorable


def purge_expired(conn: psycopg.Connection, *, now: datetime | None = None) -> None:
    conn.execute("DELETE FROM reports WHERE deleted_at < %s", ((now or utcnow()) - RESTORE_WINDOW,))
