import sqlglot
from sqlglot import exp

from .errors import GuardrailViolation
from .scope import UserScope

PROJECT = "bigquery-public-data"
DATASET = "thelook_ecommerce"
ALLOWED_TABLES = frozenset({"orders", "order_items", "products", "users"})


def parse_single_query(sql: str) -> exp.Query:
    try:
        statements = [s for s in sqlglot.parse(sql, read="bigquery") if s is not None]
    except sqlglot.errors.SqlglotError as error:
        raise GuardrailViolation("The query could not be parsed.") from error
    if len(statements) != 1:
        raise GuardrailViolation("Exactly one statement is allowed.")
    if not isinstance(statements[0], exp.Query):
        raise GuardrailViolation("Only SELECT queries are allowed.")
    return statements[0]


def check_table(table: exp.Table, cte_names: set[str]) -> None:
    if table.name in cte_names and not table.db:
        return
    in_allowed_dataset = table.db in ("", DATASET) and table.catalog in ("", PROJECT)
    if table.name not in ALLOWED_TABLES or not in_allowed_dataset:
        raise GuardrailViolation(f"Table '{table.sql(dialect='bigquery')}' is not allowed.")


def validate_sql(sql: str, scope: UserScope) -> str:
    query = parse_single_query(sql)
    cte_names = {cte.alias for cte in query.find_all(exp.CTE)}
    for table in query.find_all(exp.Table):
        check_table(table, cte_names)
    return query.sql(dialect="bigquery")
