import os

import pytest

from retail_analyst.warehouse import run_query

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("GCP_PROJECT_ID")
    or not (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    ),
    reason="BigQuery credentials absent",
)
def test_dry_run_of_a_count_on_users_fits_under_the_cap():
    sql = "SELECT COUNT(*) AS n FROM `bigquery-public-data.thelook_ecommerce.users`"
    assert run_query(sql, max_bytes_billed=10**12).rows
