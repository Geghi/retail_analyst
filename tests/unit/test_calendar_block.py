from datetime import date

from retail_analyst.agent.prompts import planner_system
from retail_analyst.metrics import calendar_block


def test_the_current_periods_are_listed_as_ready_made_ranges():
    block = calendar_block(date(2026, 11, 12))

    assert "today is 2026-11-12" in block
    assert "this month: 2026-11-01 to 2026-12-01" in block
    assert "last month: 2026-10-01 to 2026-11-01" in block
    assert "this quarter: 2026-10-01 to 2027-01-01" in block
    assert "last quarter: 2026-07-01 to 2026-10-01" in block
    assert "this year: 2026-01-01 to 2027-01-01" in block
    assert "last year: 2025-01-01 to 2026-01-01" in block


def test_a_comparison_with_the_same_days_of_last_year_is_ready_made():
    block = calendar_block(date(2026, 11, 12))

    assert "this month so far: 2026-11-01 to 2026-11-13" in block
    assert "same days last year: 2025-11-01 to 2025-11-13" in block


def test_every_month_of_this_and_last_year_is_listed_by_name():
    block = calendar_block(date(2026, 11, 12))

    assert "January 2026: 2026-01-01 to 2026-02-01" in block
    assert "December 2026: 2026-12-01 to 2027-01-01" in block
    assert "January 2025: 2025-01-01 to 2025-02-01" in block
    assert "December 2025: 2025-12-01 to 2026-01-01" in block
    assert "2024" not in block


def test_at_the_start_of_a_year_last_month_and_quarter_fall_in_the_previous_year():
    block = calendar_block(date(2026, 1, 5))

    assert "last month: 2025-12-01 to 2026-01-01" in block
    assert "last quarter: 2025-10-01 to 2026-01-01" in block
    assert "last year: 2025-01-01 to 2026-01-01" in block


def test_a_leap_day_does_not_break_the_comparison_with_last_year():
    block = calendar_block(date(2028, 2, 29))

    assert "February 2028: 2028-02-01 to 2028-03-01" in block
    assert "February 2027: 2027-02-01 to 2027-03-01" in block
    assert "this month so far: 2028-02-01 to 2028-03-01" in block
    assert "same days last year: 2027-02-01 to 2027-03-01" in block


def test_the_planner_prompt_opens_with_the_calendar_and_states_it_is_authoritative():
    system = planner_system("2026-11-12", "none")

    assert system.startswith("CALENDAR")
    assert "this month: 2026-11-01 to 2026-12-01" in system
    assert "overrides" in system.split("You are the SQL planner")[0]
