import pytest

from retail_analyst.metrics import metric_definitions, schema_description

BLOCKED = [
    "first_name",
    "last_name",
    "email",
    "street_address",
    "postal_code",
    "latitude",
    "longitude",
    "user_geom",
]


@pytest.mark.parametrize("table", ["orders", "order_items", "products", "users"])
def test_schema_names_fully_qualified_tables(table):
    assert f"bigquery-public-data.thelook_ecommerce.{table}" in schema_description()


@pytest.mark.parametrize("column", BLOCKED)
def test_schema_never_mentions_blocked_columns(column):
    assert column not in schema_description().lower()


@pytest.mark.parametrize(
    "fragment",
    [
        "order_items.order_id = orders.order_id",
        "order_items.product_id = products.id",
        "orders.user_id = users.id",
        "Shipped",
        "Complete",
        "Processing",
        "Cancelled",
        "Returned",
        "sale_price",
        "distribution_center_id",
        "GROUP BY",
        "not the executives",
    ],
)
def test_schema_carries_joins_statuses_and_columns(fragment):
    assert fragment in schema_description()


def test_metric_definitions_state_churn_and_revenue_rules():
    text = metric_definitions()
    assert "90 days" in text
    assert "Cancelled" in text and "Returned" in text
    assert "complete calendar month" in text


def test_a_total_of_orders_is_counted_once_over_the_whole_set_not_summed_by_group():
    text = metric_definitions()
    assert "COUNT(DISTINCT order_id)" in text
    assert "never add up" in text


def test_every_metric_asked_for_is_also_given_overall_not_only_by_group():
    assert "overall" in metric_definitions()
