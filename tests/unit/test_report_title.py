from retail_analyst.agent.report_text import report_title


def test_a_long_question_is_cut_at_a_word_without_a_trailing_space():
    question = (
        "What was our revenue by category in the last complete month, and which one grew the most?"
    )

    title = report_title(question)

    assert (
        title == "What was our revenue by category in the last complete month, and which one grew"
    )
    assert len(title) <= 80


def test_a_short_question_is_the_title_as_typed_with_spaces_collapsed():
    assert report_title("  Revenue   by category? ") == "Revenue by category?"


def test_an_empty_question_gets_a_generic_title():
    assert report_title("   ") == "Report"
