from retail_analyst.knowledge import Trio, find_similar, format_for_prompt, load_trios


def trio(id, question):
    return Trio(id=id, question=question, queries=[f"SELECT '{id}'"], report=f"report {id}")


TRIOS = [
    trio("b", "Why did revenue drop in Texas?"),
    trio("a", "Why did revenue drop in Ohio?"),
    trio("c", "Top customers by spend"),
]


def test_ties_break_by_id_and_non_overlapping_trios_are_dropped():
    assert [t.id for t in find_similar("revenue drop", TRIOS)] == ["a", "b"]


def test_better_overlap_ranks_first():
    assert [t.id for t in find_similar("customers spend revenue", TRIOS)][0] == "c"


def test_stopwords_alone_never_match():
    assert find_similar("why did the in", TRIOS) == []


def test_gibberish_returns_nothing():
    assert find_similar("qzxv blorp", TRIOS) == []


def test_limit_is_respected():
    assert len(find_similar("revenue drop", TRIOS, limit=1)) == 1


def test_defaults_to_the_shipped_trios():
    assert find_similar("why did revenue drop in one state compared with another")[0].id == (
        "revenue-drop-by-state"
    )


def test_revenue_by_state_ranks_the_state_trio_first():
    assert find_similar("revenue by state", load_trios())[0].id == "revenue-drop-by-state"


def test_prompt_contains_each_question_and_sql_and_says_it_is_guidance():
    text = format_for_prompt(TRIOS[:2])
    for t in TRIOS[:2]:
        assert t.question in text and t.queries[0] in text and t.report in text
    assert "guidance" in text.lower() and "not" in text.lower()
