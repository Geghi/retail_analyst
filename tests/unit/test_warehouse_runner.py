import datetime as dt
from decimal import Decimal

import pytest
from google.api_core import exceptions as gexc
from google.cloud import bigquery

from retail_analyst.warehouse import (
    QueryFailed,
    QueryTooExpensive,
    WarehouseError,
    WarehouseUnavailable,
    run_query,
)


class FakeJob:
    def __init__(self, rows, bytes_processed, error=None):
        self._rows = rows
        self.total_bytes_processed = bytes_processed
        self._error = error

    def result(self):
        if self._error:
            raise self._error
        return iter(self._rows)


class FakeClient:
    def __init__(self, rows=(), bytes_processed=100, errors=()):
        self.rows = list(rows)
        self.bytes_processed = bytes_processed
        self.errors = list(errors)
        self.calls = []

    def query(self, sql, job_config=None):
        dry = bool(job_config and job_config.dry_run)
        self.calls.append(dry)
        if dry:
            return FakeJob([], self.bytes_processed)
        error = self.errors.pop(0) if self.errors else None
        return FakeJob(self.rows, self.bytes_processed, error)


def test_a_dry_run_over_the_cap_refuses_to_execute():
    client = FakeClient(bytes_processed=5_000)
    with pytest.raises(QueryTooExpensive) as info:
        run_query("SELECT 1", client=client, max_bytes_billed=1_000)
    assert client.calls == [True]
    assert info.value.user_message


def test_the_cap_defaults_to_the_environment_variable_read_at_call_time(monkeypatch):
    monkeypatch.setenv("BQ_MAX_BYTES_BILLED", "10")
    with pytest.raises(QueryTooExpensive):
        run_query("SELECT 1", client=FakeClient(bytes_processed=11))
    monkeypatch.setenv("BQ_MAX_BYTES_BILLED", "1000")
    assert run_query("SELECT 1", client=FakeClient(bytes_processed=11)).bytes_billed == 11


def test_the_cap_defaults_to_one_billion_bytes(monkeypatch):
    monkeypatch.delenv("BQ_MAX_BYTES_BILLED", raising=False)
    with pytest.raises(QueryTooExpensive):
        run_query("SELECT 1", client=FakeClient(bytes_processed=1_000_000_001))
    assert run_query("SELECT 1", client=FakeClient(bytes_processed=1_000_000_000))


@pytest.mark.parametrize(
    "error",
    [
        gexc.ServiceUnavailable("x"),
        gexc.InternalServerError("x"),
        gexc.TooManyRequests("x"),
        gexc.DeadlineExceeded("x"),
    ],
)
def test_transient_errors_raise_unavailable_after_exactly_one_attempt(error):
    client = FakeClient(errors=[error] * 10)
    with pytest.raises(WarehouseUnavailable) as info:
        run_query("SELECT 1", client=client)
    assert client.calls.count(False) == 1
    assert info.value.user_message


def test_a_failure_building_the_default_client_is_a_safe_warehouse_error(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("no creds in /home/secret/key.json")

    monkeypatch.setattr(bigquery, "Client", broken)
    with pytest.raises(WarehouseError) as info:
        run_query("SELECT 1")
    assert "secret" not in info.value.user_message


def test_a_bad_request_carries_a_truncated_reason():
    client = FakeClient(errors=[gexc.BadRequest("Unrecognized name: foo " + "x" * 800)])
    with pytest.raises(QueryFailed) as info:
        run_query("SELECT foo", client=client)
    assert client.calls.count(False) == 1
    assert info.value.reason.startswith("Unrecognized name: foo")
    assert len(info.value.reason) <= 500
    assert "foo" not in info.value.user_message


def test_a_bad_request_at_dry_run_is_a_query_failure():
    class BadDry(FakeClient):
        def query(self, sql, job_config=None):
            raise gexc.BadRequest("Syntax error")

    with pytest.raises(QueryFailed):
        run_query("SELEC", client=BadDry())


def test_any_other_google_error_is_wrapped():
    client = FakeClient(errors=[gexc.Forbidden("project secret-proj denied")])
    with pytest.raises(WarehouseError) as info:
        run_query("SELECT 1", client=client)
    assert "secret-proj" not in info.value.user_message


def test_rows_are_json_friendly_dicts():
    rows = [
        {
            "ts": dt.datetime(2024, 1, 2, 3, 4, 5),
            "d": dt.date(2024, 1, 2),
            "amount": Decimal("1.5"),
            "n": 3,
        }
    ]
    result = run_query("SELECT 1", client=FakeClient(rows=rows))
    assert result.rows == [{"ts": "2024-01-02T03:04:05", "d": "2024-01-02", "amount": 1.5, "n": 3}]
    assert result.is_empty is False


def test_rows_are_truncated_to_max_rows():
    result = run_query(
        "SELECT 1", client=FakeClient(rows=[{"n": i} for i in range(10)]), max_rows=4
    )
    assert [r["n"] for r in result.rows] == [0, 1, 2, 3]


def test_zero_rows_is_empty():
    result = run_query("SELECT 1", client=FakeClient(rows=[]))
    assert result.is_empty is True and result.rows == []
