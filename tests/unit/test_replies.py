import json

from retail_analyst.agent.replies import readable_answer


def test_a_report_written_in_a_text_field_is_not_lost():
    reply = json.dumps(
        {"answer": "One line.", "text": "Summary: full report.", "follow_up_queries": []}
    )

    text, follow_ups = readable_answer(reply)

    assert "One line." in text and "Summary: full report." in text
    assert follow_ups == []


def test_a_field_repeating_the_answer_is_shown_once():
    reply = json.dumps({"answer": "Same text.", "text": "Same text."})

    assert readable_answer(reply)[0] == "Same text."
