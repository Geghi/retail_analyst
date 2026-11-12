import uuid

import pytest

from retail_analyst.reports import list_reports, save_report
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


def test_saved_report_is_listed_for_its_owner_only(conn):
    alice, bob = new_user(), new_user()
    saved = save_report(conn, alice, "Q1 revenue", "Revenue grew", "conv-1")
    assert list_reports(conn, alice) == [saved]
    assert list_reports(conn, bob) == []
