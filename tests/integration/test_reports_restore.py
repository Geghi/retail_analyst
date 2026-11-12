import uuid
from datetime import UTC, datetime, timedelta

import pytest

from retail_analyst.reports import (
    NotRestorable,
    confirm_delete,
    list_reports,
    purge_expired,
    request_delete,
    restore_report,
    save_report,
)
from retail_analyst.storage import connect, create_tables

URL = "postgresql://analyst:analyst@localhost:5432/analyst"


@pytest.fixture(scope="module")
def conn():
    connection = connect(URL)
    create_tables(connection)
    yield connection
    connection.close()


def deleted_report(conn, user, deleted_at):
    report = save_report(conn, user, "t", "b", "c")
    pending = request_delete(conn, user, report_ids=[report.id], now=deleted_at)
    confirm_delete(conn, user, pending.id, now=deleted_at)
    return report


def new_user():
    return f"user-{uuid.uuid4()}"


def test_soft_delete_and_restore_round_trip(conn):
    user = new_user()
    report = deleted_report(conn, user, datetime.now(UTC))
    assert list_reports(conn, user) == []
    restore_report(conn, user, report.id)
    restored = list_reports(conn, user)
    assert [r.id for r in restored] == [report.id]
    assert restored[0].deleted_at is None


def test_restore_after_thirty_days_is_refused(conn):
    user = new_user()
    start = datetime.now(UTC)
    report = deleted_report(conn, user, start)
    with pytest.raises(NotRestorable):
        restore_report(conn, user, report.id, now=start + timedelta(days=30, seconds=1))
    restore_report(conn, user, report.id, now=start + timedelta(days=29))


def test_restore_of_live_or_unknown_report_is_refused(conn):
    user = new_user()
    live = save_report(conn, user, "t", "b", "c")
    with pytest.raises(NotRestorable):
        restore_report(conn, user, live.id)
    with pytest.raises(NotRestorable):
        restore_report(conn, user, uuid.uuid4())


def test_other_user_cannot_restore(conn):
    alice, bob = new_user(), new_user()
    report = deleted_report(conn, alice, datetime.now(UTC))
    with pytest.raises(NotRestorable):
        restore_report(conn, bob, report.id)
    assert list_reports(conn, alice) == []


def test_purge_removes_only_rows_deleted_more_than_thirty_days_ago(conn):
    user = new_user()
    now = datetime.now(UTC)
    old = deleted_report(conn, user, now - timedelta(days=31))
    recent = deleted_report(conn, user, now - timedelta(days=29))
    live = save_report(conn, user, "t", "b", "c")
    purge_expired(conn, now=now)
    remaining = {r.id for r in list_reports(conn, user, include_deleted=True)}
    assert remaining == {recent.id, live.id}
    assert old.id not in remaining
