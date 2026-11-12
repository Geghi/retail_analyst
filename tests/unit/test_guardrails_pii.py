import pytest

from retail_analyst.guardrails import GuardrailViolation, UserScope, validate_sql

SCOPE = UserScope(user_id="alice", allowed_categories=frozenset({"Jeans"}))
USERS = "`bigquery-public-data.thelook_ecommerce.users`"


@pytest.mark.parametrize(
    "sql",
    [
        f"SELECT email FROM {USERS}",
        f"SELECT u.first_name AS who FROM {USERS} u",
        f"SELECT * FROM {USERS}",
        f"SELECT u.* FROM {USERS} u",
        f"SELECT * FROM (SELECT last_name FROM {USERS})",
        f"WITH x AS (SELECT * FROM {USERS}) SELECT * FROM x",
        f"SELECT COUNT(*) FROM {USERS} WHERE postal_code = '10001'",
        f"SELECT COUNT(*) FROM {USERS} ORDER BY latitude",
        f"SELECT COUNT(*) FROM {USERS} u JOIN {USERS} v ON u.street_address = v.street_address",
        f"SELECT longitude, user_geom FROM {USERS}",
        f"SELECT city FROM {USERS}",
        f"WITH x AS (SELECT city FROM {USERS}) SELECT city, COUNT(*) FROM x GROUP BY city",
        f"SELECT city, state FROM {USERS} GROUP BY city, state",
    ],
)
def test_pii_columns_are_refused(sql):
    with pytest.raises(GuardrailViolation):
        validate_sql(sql, SCOPE)


@pytest.mark.parametrize(
    "sql",
    [
        f"SELECT country, COUNT(*) AS n FROM {USERS} GROUP BY country",
        f"SELECT city, state, COUNT(DISTINCT id) FROM {USERS} GROUP BY city, state",
        f"SELECT COUNT(*) FROM {USERS}",
        f"SELECT id, age FROM {USERS}",
    ],
)
def test_aggregates_and_safe_columns_on_users_are_accepted(sql):
    validate_sql(sql, SCOPE)
