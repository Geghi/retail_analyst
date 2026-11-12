import pytest
from google.api_core import exceptions as gexc
from google.cloud import bigquery
from test_warehouse_runner import FakeClient

from retail_analyst.warehouse import (
    BigQueryClient,
    QueryTooExpensive,
    WarehouseError,
)


class Field:
    def __init__(self, name, field_type, mode="NULLABLE", description=None):
        self.name, self.field_type, self.mode, self.description = (
            name,
            field_type,
            mode,
            description,
        )


class SchemaClient(FakeClient):
    def __init__(self, fields=(), error=None):
        super().__init__()
        self.fields, self.error, self.requested = list(fields), error, []

    def get_table(self, ref):
        self.requested.append(ref)
        if self.error:
            raise self.error
        return type("Table", (), {"schema": self.fields})()


def test_execute_query_returns_rows_and_refuses_queries_over_the_cost_cap():
    client = BigQueryClient(client=FakeClient(rows=[{"n": 1}], bytes_processed=10))

    assert client.execute_query("SELECT 1").rows == [{"n": 1}]
    with pytest.raises(QueryTooExpensive):
        client.execute_query("SELECT 1", max_bytes_billed=5)


def test_get_table_schema_describes_each_column_of_a_dataset_table():
    fake = SchemaClient(
        [Field("id", "INTEGER", "REQUIRED", "primary key"), Field("name", "STRING")]
    )
    client = BigQueryClient(dataset_id="proj.data", client=fake)

    schema = client.get_table_schema("users")

    assert fake.requested == ["proj.data.users"]
    assert schema == [
        {"name": "id", "type": "INTEGER", "mode": "REQUIRED", "description": "primary key"},
        {"name": "name", "type": "STRING", "mode": "NULLABLE", "description": ""},
    ]


def test_the_default_dataset_is_the_public_thelook_ecommerce_one():
    fake = SchemaClient()

    BigQueryClient(client=fake).get_table_schema("orders")

    assert fake.requested == ["bigquery-public-data.thelook_ecommerce.orders"]


def test_a_missing_table_is_a_safe_warehouse_error():
    client = BigQueryClient(client=SchemaClient(error=gexc.NotFound("secret-project.x not found")))

    with pytest.raises(WarehouseError) as info:
        client.get_table_schema("nope")

    assert "secret-project" not in info.value.user_message


def test_a_failure_creating_the_google_client_is_a_safe_warehouse_error(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("no creds in /home/secret/key.json")

    monkeypatch.setattr(bigquery, "Client", broken)

    with pytest.raises(WarehouseError) as info:
        BigQueryClient()

    assert "secret" not in info.value.user_message
