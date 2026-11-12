from retail_analyst.agent.prompts import planner_system


def test_the_planner_is_told_to_let_bigquery_compute_relative_dates():
    system = planner_system("2026-11-12", "none")

    assert "CURRENT_DATE()" in system
    assert "never write a date you worked out yourself" in system
