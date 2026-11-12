import datetime as dt
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from google.api_core import exceptions as gexc
from google.cloud import bigquery

from .errors import QueryFailed, QueryTooExpensive, WarehouseError, WarehouseUnavailable

DEFAULT_MAX_BYTES_BILLED = 1_000_000_000
DEFAULT_DATASET = "bigquery-public-data.thelook_ecommerce"
TRANSIENT = (
    gexc.ServiceUnavailable,
    gexc.InternalServerError,
    gexc.TooManyRequests,
    gexc.DeadlineExceeded,
)

_default: "BigQueryClient | None" = None


@dataclass(frozen=True)
class QueryResult:
    rows: list[dict]
    bytes_billed: int
    is_empty: bool


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


class BigQueryClient:
    """BigQuery access with a cost cap, typed errors and JSON-friendly rows."""

    def __init__(
        self,
        project_id: str | None = None,
        dataset_id: str = DEFAULT_DATASET,
        client: Any = None,
    ) -> None:
        """Create the client.

        Args:
            project_id: Google Cloud project ID. Defaults to GCP_PROJECT_ID, then to the
                project of the default credentials.
            dataset_id: Dataset that table names are resolved against.
            client: An existing google bigquery client, for tests.
        """
        self.dataset_id = dataset_id
        if client is not None:
            self.client = client
            return
        logging.info("Initializing BigQuery client")
        try:
            self.client = bigquery.Client(project=project_id or os.environ.get("GCP_PROJECT_ID"))
        except Exception as error:
            logging.error("Failed to initialize BigQuery client: %s", type(error).__name__)
            raise WarehouseError("The data warehouse is not configured correctly.") from error
        logging.info("BigQuery client initialized for dataset: %s", self.dataset_id)

    def execute_query(
        self, sql_query: str, *, max_bytes_billed: int | None = None, max_rows: int = 1000
    ) -> QueryResult:
        """Run a SQL query after a dry run against the byte cap.

        Returns:
            QueryResult with JSON-friendly rows, capped at max_rows.

        Raises:
            QueryTooExpensive: the dry run is over the cap.
            QueryFailed: BigQuery rejected the query; carries its reason.
            WarehouseUnavailable: a transient Google error, safe to retry.
            WarehouseError: any other failure.
        """
        try:
            cap = _cap(max_bytes_billed)
            dry = self.client.query(sql_query, job_config=bigquery.QueryJobConfig(dry_run=True))
            if (dry.total_bytes_processed or 0) > cap:
                raise QueryTooExpensive(
                    "This question would scan too much data. "
                    "Try narrowing the date range or columns."
                )
            logging.info("Executing BigQuery query")
            result = _execute(self.client, sql_query, cap, max_rows)
            logging.info("Query completed, returned %d rows", len(result.rows))
            return result
        except Exception as error:
            logging.error("BigQuery execution failed: %s", type(error).__name__)
            raise _as_warehouse_error(error) from error

    def get_table_schema(self, table_name: str) -> list[dict[str, str]]:
        """Describe the columns of a table of the dataset (name, type, mode, description)."""
        try:
            table = self.client.get_table(f"{self.dataset_id}.{table_name}")
        except Exception as error:
            logging.error("Failed to get schema for table %s: %s", table_name, type(error).__name__)
            raise WarehouseError("The table description could not be read.") from error
        return [
            {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description or "",
            }
            for field in table.schema
        ]


def _as_warehouse_error(error: Exception) -> WarehouseError:
    if isinstance(error, WarehouseError):
        return error
    if isinstance(error, gexc.BadRequest):
        return QueryFailed("The query could not be run.", error.message)
    if isinstance(error, TRANSIENT):
        return WarehouseUnavailable(
            "The data warehouse is temporarily unavailable. Please try again shortly."
        )
    return WarehouseError("The data warehouse returned an error.")


def run_query(
    sql: str, *, client=None, max_bytes_billed: int | None = None, max_rows: int = 1000
) -> QueryResult:
    global _default
    if client is not None:
        warehouse = BigQueryClient(client=client)
    else:
        _default = _default or BigQueryClient()
        warehouse = _default
    return warehouse.execute_query(sql, max_bytes_billed=max_bytes_billed, max_rows=max_rows)
