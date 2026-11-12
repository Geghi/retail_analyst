from sqlglot import exp

from .errors import GuardrailViolation
from .scope import UserScope

SCOPED_TABLES = frozenset({"products", "order_items"})


def sibling(table: exp.Table, name: str) -> exp.Table:
    other = table.copy()
    other.set("alias", None)
    other.set("this", exp.to_identifier(name))
    return other


def in_scope_products(table: exp.Table, categories: list[str]) -> exp.Select:
    return (
        exp.select("id")
        .from_(sibling(table, "products"))
        .where(exp.column("category").isin(*[exp.Literal.string(c) for c in categories]))
    )


def scoped_source(table: exp.Table, categories: list[str]) -> exp.Select:
    if table.name == "products":
        return (
            exp.select("*")
            .from_(sibling(table, "products"))
            .where(exp.column("category").isin(*[exp.Literal.string(c) for c in categories]))
        )
    return (
        exp.select("*")
        .from_(sibling(table, "order_items"))
        .where(exp.column("product_id").isin(query=in_scope_products(table, categories)))
    )


def scope_products(query: exp.Query, scope: UserScope, cte_names: set[str]) -> exp.Query:
    if not scope.allowed_categories:
        raise GuardrailViolation("No product categories are allowed for this user.")
    categories = sorted(scope.allowed_categories)
    targets = [
        t
        for t in query.find_all(exp.Table)
        if t.name in SCOPED_TABLES and not (t.name in cte_names and not t.db)
    ]
    for table in targets:
        alias = table.alias or table.name
        subquery = scoped_source(table, categories).subquery(alias)
        table.replace(subquery)
    return query
