import pytest

from retail_analyst.guardrails import GuardrailViolation, UserScope, validate_sql

SCOPE = UserScope(user_id="alice", allowed_categories=frozenset({"Jeans"}))


def test_a_single_select_on_an_allowed_table_is_accepted():
    sql = (
        "SELECT category, COUNT(*) AS n "
        "FROM `bigquery-public-data.thelook_ecommerce.products` GROUP BY category"
    )
    assert "products" in validate_sql(sql, SCOPE)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM `bigquery-public-data.thelook_ecommerce.orders` WHERE TRUE",
        "DROP TABLE orders",
        "UPDATE orders SET status = 'Cancelled' WHERE TRUE",
        "SELECT 1; DROP TABLE orders",
        "SELECT * FROM `other-project.sales.secrets`",
        "SELECT * FROM `bigquery-public-data.other_dataset.orders`",
        "not sql at all (((",
        "",
    ],
)
def test_anything_but_a_select_on_allowed_tables_is_refused(sql):
    with pytest.raises(GuardrailViolation):
        validate_sql(sql, SCOPE)
