import pytest

from retail_analyst.guardrails import UserScope, validate_sql
from retail_analyst.knowledge import load_trios

SCOPE = UserScope(user_id="test", allowed_categories=frozenset({"Jeans"}))
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
TRIOS = load_trios()
QUERIES = [(t.id, q) for t in TRIOS for q in t.queries]


def test_five_trios_with_unique_ids():
    assert len({t.id for t in TRIOS}) == len(TRIOS) >= 5


@pytest.mark.parametrize(("trio_id", "sql"), QUERIES)
def test_every_shipped_query_passes_the_guardrails(trio_id, sql):
    validate_sql(sql, SCOPE)


@pytest.mark.parametrize(("trio_id", "sql"), QUERIES)
def test_no_query_names_a_personal_column(trio_id, sql):
    assert not [c for c in BLOCKED if c in sql.lower()]


@pytest.mark.parametrize("trio", TRIOS, ids=lambda t: t.id)
def test_reports_separate_facts_from_hypotheses_and_list_actions(trio):
    for heading in ("Observed", "Hypotheses", "Actions"):
        assert heading in trio.report


def test_a_period_comparison_example_gives_overall_and_per_category_figures():
    (trio,) = [t for t in TRIOS if t.id == "period-comparison"]
    assert len(trio.queries) == 2


@pytest.mark.parametrize(("trio_id", "sql"), QUERIES)
def test_no_query_hardcodes_a_year(trio_id, sql):
    import re

    assert not re.search(r"\b20\d\d\b", sql)
