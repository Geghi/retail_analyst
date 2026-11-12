from datetime import date

import pytest

from retail_analyst.metrics import churn_cutoff, last_complete_month


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 12), (date(2026, 10, 1), date(2026, 11, 1))),
        (date(2026, 11, 1), (date(2026, 10, 1), date(2026, 11, 1))),
        (date(2026, 11, 30), (date(2026, 10, 1), date(2026, 11, 1))),
        (date(2026, 1, 15), (date(2025, 12, 1), date(2026, 1, 1))),
        (date(2026, 1, 1), (date(2025, 12, 1), date(2026, 1, 1))),
        (date(2026, 1, 31), (date(2025, 12, 1), date(2026, 1, 1))),
        (date(2026, 3, 10), (date(2026, 2, 1), date(2026, 3, 1))),
    ],
)
def test_last_complete_month_is_half_open(today, expected):
    assert last_complete_month(today) == expected


def test_churn_cutoff_defaults_to_90_days():
    assert churn_cutoff(date(2026, 11, 12)) == date(2026, 8, 14)


def test_churn_cutoff_accepts_other_windows():
    assert churn_cutoff(date(2026, 11, 12), days=30) == date(2026, 10, 13)
