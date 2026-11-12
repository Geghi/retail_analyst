from retail_analyst.agent.prompts import planner_system


def test_the_planner_is_told_to_let_bigquery_compute_relative_dates():
    system = planner_system("2026-11-12", "none")

    assert "CURRENT_DATE()" in system
    assert "never write a date you worked out yourself" in system


def test_the_analyst_must_describe_the_direction_of_each_change_as_the_numbers_show_it():
    from retail_analyst.agent.prompts import analyst_system

    system = analyst_system("persona", "2026-11-12")

    assert "rose or fell" in system
