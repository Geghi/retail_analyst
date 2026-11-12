import datetime as dt
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from google.api_core import exceptions as gexc
from google.cloud import bigquery

from .errors import QueryFailed, QueryTooExpensive, WarehouseError, WarehouseUnavailable

DEFAULT_MAX_BYTES_BILLED = 1_000_000_000
TRANSIENT = (
    gexc.ServiceUnavailable,
    gexc.InternalServerError,
    gexc.TooManyRequests,
    gexc.DeadlineExceeded,
)

_default_client: bigquery.Client | None = None


@dataclass(frozen=True)
class QueryResult:
    rows: list[dict]
    bytes_billed: int
    is_empty: bool


def _client() -> bigquery.Client:
    global _default_client
    if _default_client is None:
        _default_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
    return _default_client


def _json_value(value: Any) -> Any:
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row(row: Any) -> dict:
    return {key: _json_value(value) for key, value in dict(row).items()}


def _cap(max_bytes_billed: int | None) -> int:
    if max_bytes_billed is not None:
        return max_bytes_billed
    return int(os.environ.get("BQ_MAX_BYTES_BILLED", DEFAULT_MAX_BYTES_BILLED))


def _execute(client, sql: str, cap: int, max_rows: int) -> QueryResult:
    job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=cap))
    rows = []
    for row in job.result():
        rows.append(_row(row))
        if len(rows) == max_rows:
            break
    return QueryResult(rows, job.total_bytes_processed or 0, not rows)


def run_query(
    sql: str,
    *,
    client=None,
    max_bytes_billed: int | None = None,
    max_rows: int = 1000,
) -> QueryResult:
    try:
        client = client or _client()
        cap = _cap(max_bytes_billed)
        dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
        if (dry.total_bytes_processed or 0) > cap:
            raise QueryTooExpensive(
                "This question would scan too much data. Try narrowing the date range or columns."
            )
        return _execute(client, sql, cap, max_rows)
    except WarehouseError:
        raise
    except gexc.BadRequest as error:
        raise QueryFailed("The query could not be run.", error.message) from error
    except TRANSIENT as error:
        raise WarehouseUnavailable(
            "The data warehouse is temporarily unavailable. Please try again shortly."
        ) from error
    except Exception as error:
        raise WarehouseError("The data warehouse returned an error.") from error
