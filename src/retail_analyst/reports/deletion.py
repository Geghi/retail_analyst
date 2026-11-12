import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import class_row

from .errors import NothingToDelete, PendingNotFound
from .store import Report, utcnow

PENDING_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class PendingDeletion:
    id: uuid.UUID
    user_id: str
    reports: list[Report]
    created_at: datetime


def request_delete(
    conn: psycopg.Connection,
    user_id: str,
    *,
    text_match: str | None = None,
    conversation_id: str | None = None,
    report_ids: list[uuid.UUID] | None = None,
    now: datetime | None = None,
) -> PendingDeletion:
    if text_match is None and conversation_id is None and report_ids is None:
        raise NothingToDelete
    with conn.cursor(row_factory=class_row(Report)) as cur:
        reports = cur.execute(
            "SELECT * FROM reports WHERE user_id = %(user)s AND deleted_at IS NULL"
            " AND (%(text)s::text IS NULL OR position(lower(%(text)s) in lower(title)) > 0"
            "      OR position(lower(%(text)s) in lower(body)) > 0)"
            " AND (%(conv)s::text IS NULL OR conversation_id = %(conv)s)"
            " AND (%(ids)s::uuid[] IS NULL OR id = ANY(%(ids)s))"
            " ORDER BY created_at, id",
            {"user": user_id, "text": text_match, "conv": conversation_id, "ids": report_ids},
        ).fetchall()
    if not reports:
        raise NothingToDelete
    pending = PendingDeletion(uuid.uuid4(), user_id, reports, now or utcnow())
    conn.execute(
        "INSERT INTO pending_deletions (id, user_id, report_ids, created_at)"
        " VALUES (%s, %s, %s, %s)",
        (pending.id, user_id, [r.id for r in reports], pending.created_at),
    )
    return pending


def take_pending(
    conn: psycopg.Connection, user_id: str, pending_id: uuid.UUID
) -> tuple[list[uuid.UUID], datetime]:
    row = conn.execute(
        "DELETE FROM pending_deletions WHERE id = %s AND user_id = %s"
        " RETURNING report_ids, created_at",
        (pending_id, user_id),
    ).fetchone()
    if row is None:
        raise PendingNotFound
    return row


def confirm_delete(
    conn: psycopg.Connection, user_id: str, pending_id: uuid.UUID, *, now: datetime | None = None
) -> list[Report]:
    now = now or utcnow()
    with conn.transaction():
        report_ids, created_at = take_pending(conn, user_id, pending_id)
        if now - created_at > PENDING_TTL:
            raise PendingNotFound
        with conn.cursor(row_factory=class_row(Report)) as cur:
            return cur.execute(
                "UPDATE reports SET deleted_at = %s WHERE user_id = %s AND id = ANY(%s)"
                " AND deleted_at IS NULL RETURNING *",
                (now, user_id, report_ids),
            ).fetchall()


def cancel_delete(conn: psycopg.Connection, user_id: str, pending_id: uuid.UUID) -> None:
    take_pending(conn, user_id, pending_id)
