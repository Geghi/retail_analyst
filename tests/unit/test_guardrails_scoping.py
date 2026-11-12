import pytest

from retail_analyst.guardrails import GuardrailViolation, UserScope, validate_sql

SCOPE = UserScope(user_id="alice", allowed_categories=frozenset({"Jeans"}))
P = "`bigquery-public-data.thelook_ecommerce.products`"
OI = "`bigquery-public-data.thelook_ecommerce.order_items`"


def test_products_become_a_category_filtered_subquery_keeping_the_alias():
    sql = validate_sql(f"SELECT p.name FROM {P} AS p", SCOPE)
    assert "FROM (SELECT * FROM" in sql
    assert "category IN ('Jeans')" in sql
    assert ") AS p" in sql


def test_unaliased_references_keep_the_table_name_as_alias():
    sql = validate_sql(f"SELECT products.name FROM {P}", SCOPE)
    assert ") AS products" in sql


def test_order_items_are_filtered_through_their_product():
    sql = validate_sql(f"SELECT SUM(sale_price) FROM {OI} oi", SCOPE)
    assert "product_id IN (SELECT id FROM" in sql
    assert "category IN ('Jeans')" in sql
    assert ") AS oi" in sql


def test_references_in_ctes_subqueries_and_joins_are_all_scoped():
    sql = validate_sql(
        f"WITH t AS (SELECT * FROM {OI}) "
        f"SELECT p.name FROM {P} p JOIN t ON t.product_id = p.id "
        f"WHERE p.id IN (SELECT product_id FROM {OI})",
        SCOPE,
    )
    assert sql.count("category IN ('Jeans')") == 3


def test_multiple_categories_are_all_listed():
    scope = UserScope(user_id="bob", allowed_categories=frozenset({"Jeans", "Socks"}))
    sql = validate_sql(f"SELECT 1 FROM {P}", scope)
    assert "'Jeans'" in sql and "'Socks'" in sql


def test_a_malicious_category_is_escaped_as_a_literal():
    scope = UserScope(user_id="eve", allowed_categories=frozenset({"x') OR 1=1 --"}))
    sql = validate_sql(f"SELECT 1 FROM {P}", scope)
    assert "category IN ('x\\') OR 1=1 --')" in sql


def test_no_allowed_categories_is_refused():
    with pytest.raises(GuardrailViolation):
        validate_sql(f"SELECT 1 FROM {P}", UserScope("nobody", frozenset()))


def test_queries_without_products_are_unchanged_in_scope():
    sql = validate_sql(
        "SELECT COUNT(*) FROM `bigquery-public-data.thelook_ecommerce.orders`", SCOPE
    )
    assert "Jeans" not in sql
