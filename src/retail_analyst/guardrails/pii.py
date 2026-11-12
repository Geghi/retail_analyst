from sqlglot import exp

from .errors import GuardrailViolation

BLOCKED_COLUMNS = frozenset(
    {
        "first_name",
        "last_name",
        "email",
        "street_address",
        "postal_code",
        "latitude",
        "longitude",
        "user_geom",
    }
)
AGGREGATE_ONLY_COLUMNS = frozenset({"city", "state", "country"})


def is_select_all(star: exp.Star) -> bool:
    return not isinstance(star.parent, exp.Count)


def is_aggregate_query(select: exp.Select | None) -> bool:
    return (
        select is not None
        and bool(select.args.get("group"))
        and any(True for _ in select.find_all(exp.AggFunc))
    )


def check_pii(query: exp.Query) -> None:
    touches_users = any(table.name == "users" for table in query.find_all(exp.Table))
    for column in query.find_all(exp.Column):
        name = column.name.lower()
        if name in BLOCKED_COLUMNS:
            raise GuardrailViolation(f"Column '{name}' is personal data and is not allowed.")
        if name in AGGREGATE_ONLY_COLUMNS and not is_aggregate_query(
            column.find_ancestor(exp.Select)
        ):
            raise GuardrailViolation(f"Column '{name}' is only allowed as a grouping dimension.")
    if touches_users and any(is_select_all(star) for star in query.find_all(exp.Star)):
        raise GuardrailViolation("SELECT * over users would expose personal data.")
