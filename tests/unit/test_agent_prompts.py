from retail_analyst.agent.prompts import planner_system


def test_the_planner_is_told_to_let_bigquery_compute_relative_dates():
    system = planner_system("2026-11-12", "none")

    assert "CURRENT_DATE()" in system
    assert "never write a date you worked out yourself" in system


def test_the_analyst_must_describe_the_direction_of_each_change_as_the_numbers_show_it():
    from retail_analyst.agent.prompts import analyst_system

    system = analyst_system("persona", "2026-11-12")

    assert "rose or fell" in system


def test_the_analyst_is_told_when_a_result_was_cut_to_the_first_rows():
    from retail_analyst.agent.prompts import analyst_prompt

    rows = [{"brand": f"b{i}"} for i in range(120)]

    prompt = analyst_prompt("by brand?", [{"sql": "SELECT brand", "rows": rows}])

    assert 'rows_shown="50"' in prompt
    assert 'rows_total="120"' in prompt


def test_the_analyst_must_say_which_part_of_the_question_it_could_not_answer():
    from retail_analyst.agent.prompts import analyst_system

    system = analyst_system("persona", "2026-11-12")

    assert "say which part" in system


def test_the_planner_limits_breakdowns_with_many_values_to_the_top_ones():
    system = planner_system("2026-11-12", "none")

    assert "ORDER BY" in system and "LIMIT 10" in system


def test_the_planner_treats_any_request_to_keep_the_last_report_as_save_report():
    system = planner_system("2026-11-12", "none")

    assert "save, keep, store or create the report you just wrote" in system
    assert "in any language" in system


def test_the_analyst_is_told_to_put_the_whole_report_in_the_answer_field():
    from retail_analyst.agent.prompts import analyst_system

    assert "inside the answer field" in analyst_system("persona", "2026-11-12")
