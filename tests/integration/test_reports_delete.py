import uuid
from datetime import UTC, datetime, timedelta

import pytest

from retail_analyst.reports import (
    NothingToDelete,
    PendingNotFound,
    cancel_delete,
    confirm_delete,
    list_reports,
    request_delete,
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


def new_user():
    return f"user-{uuid.uuid4()}"


def test_request_delete_changes_nothing_and_lists_matches(conn):
    user = new_user()
    hit = save_report(conn, user, "Client X churn", "body", "c1")
    save_report(conn, user, "Other", "body", "c1")
    pending = request_delete(conn, user, text_match="client x")
    assert [r.id for r in pending.reports] == [hit.id]
    assert len(list_reports(conn, user)) == 2


def test_text_match_covers_body_and_is_case_insensitive(conn):
    user = new_user()
    hit = save_report(conn, user, "t", "mentions CLIENT X here", "c1")
    pending = request_delete(conn, user, text_match="Client x")
    assert [r.id for r in pending.reports] == [hit.id]


def test_text_match_with_quotes_and_wildcards_is_literal(conn):
    user = new_user()
    tricky = save_report(conn, user, "O'Brien'; DROP TABLE reports;--", "100% sure", "c1")
    save_report(conn, user, "plain", "plain", "c1")
    for text in ("O'Brien'; DROP TABLE reports;--", "100%"):
        assert [r.id for r in request_delete(conn, user, text_match=text).reports] == [tricky.id]
    with pytest.raises(NothingToDelete):
        request_delete(conn, user, text_match="p_ain")


def test_conversation_id_selects_every_report_of_the_conversation(conn):
    user = new_user()
    a = save_report(conn, user, "a", "x", "conv-a")
    b = save_report(conn, user, "b", "x", "conv-a")
    save_report(conn, user, "c", "x", "conv-b")
    pending = request_delete(conn, user, conversation_id="conv-a")
    assert {r.id for r in pending.reports} == {a.id, b.id}


def test_report_ids_select_given_reports(conn):
    user = new_user()
    a = save_report(conn, user, "a", "x", "c")
    save_report(conn, user, "b", "x", "c")
    assert [r.id for r in request_delete(conn, user, report_ids=[a.id]).reports] == [a.id]


def test_zero_matches_or_no_criteria_raises_nothing_to_delete(conn):
    user = new_user()
    save_report(conn, user, "a", "x", "c")
    with pytest.raises(NothingToDelete):
        request_delete(conn, user, text_match="absent")
    with pytest.raises(NothingToDelete):
        request_delete(conn, user)


def test_confirm_deletes_exactly_the_matched_set(conn):
    user = new_user()
    old = save_report(conn, user, "Client X old", "x", "c")
    pending = request_delete(conn, user, text_match="client x")
    later = save_report(conn, user, "Client X later", "x", "c")
    deleted = confirm_delete(conn, user, pending.id)
    assert [r.id for r in deleted] == [old.id]
    assert deleted[0].deleted_at is not None
    assert [r.id for r in list_reports(conn, user)] == [later.id]
    assert [r.id for r in list_reports(conn, user, include_deleted=True)] == [old.id, later.id]


def test_pending_deletion_is_single_use(conn):
    user = new_user()
    save_report(conn, user, "a", "x", "c")
    pending = request_delete(conn, user, text_match="a")
    confirm_delete(conn, user, pending.id)
    with pytest.raises(PendingNotFound):
        confirm_delete(conn, user, pending.id)


def test_cancel_discards_pending_and_deletes_nothing(conn):
    user = new_user()
    save_report(conn, user, "a", "x", "c")
    pending = request_delete(conn, user, text_match="a")
    cancel_delete(conn, user, pending.id)
    with pytest.raises(PendingNotFound):
        confirm_delete(conn, user, pending.id)
    assert len(list_reports(conn, user)) == 1


def test_pending_expires_after_ten_minutes(conn):
    user = new_user()
    save_report(conn, user, "a", "x", "c")
    start = datetime.now(UTC)
    pending = request_delete(conn, user, text_match="a", now=start)
    with pytest.raises(PendingNotFound):
        confirm_delete(conn, user, pending.id, now=start + timedelta(minutes=10, seconds=1))
    assert len(list_reports(conn, user)) == 1


def test_pending_confirmed_just_before_expiry(conn):
    user = new_user()
    save_report(conn, user, "a", "x", "c")
    start = datetime.now(UTC)
    pending = request_delete(conn, user, text_match="a", now=start)
    assert len(confirm_delete(conn, user, pending.id, now=start + timedelta(minutes=9))) == 1


def test_other_user_cannot_see_match_or_confirm(conn):
    alice, bob = new_user(), new_user()
    mine = save_report(conn, alice, "Client X", "x", "conv-shared")
    with pytest.raises(NothingToDelete):
        request_delete(conn, bob, text_match="client x")
    with pytest.raises(NothingToDelete):
        request_delete(conn, bob, conversation_id="conv-shared")
    with pytest.raises(NothingToDelete):
        request_delete(conn, bob, report_ids=[mine.id])
    pending = request_delete(conn, alice, text_match="client x")
    with pytest.raises(PendingNotFound):
        confirm_delete(conn, bob, pending.id)
    with pytest.raises(PendingNotFound):
        cancel_delete(conn, bob, pending.id)
    assert len(confirm_delete(conn, alice, pending.id)) == 1
