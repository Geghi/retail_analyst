from datetime import date, timedelta

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def last_complete_month(today: date) -> tuple[date, date]:
    end = today.replace(day=1)
    start = (end - timedelta(days=1)).replace(day=1)
    return start, end


def churn_cutoff(today: date, days: int = 90) -> date:
    return today - timedelta(days=days)


def _first_of_month(year: int, month: int) -> date:
    return date(year + (month - 1) // 12, (month - 1) % 12 + 1, 1)


def _same_day_in_year(day: date, year: int) -> date:
    last_day = (_first_of_month(year, day.month + 1) - timedelta(days=1)).day
    return day.replace(year=year, day=min(day.day, last_day))


def _range(start: date, end: date) -> str:
    return f"{start.isoformat()} to {end.isoformat()}"


def calendar_block(today: date) -> str:
    """Ready-made date ranges (end exclusive) so the model never works out a date itself."""
    month = _first_of_month(today.year, today.month)
    quarter = _first_of_month(today.year, (today.month - 1) // 3 * 3 + 1)
    tomorrow = today + timedelta(days=1)
    last_year_today = _same_day_in_year(today, today.year - 1)
    lines = [
        f"CALENDAR (today is {today.isoformat()}; this calendar overrides any year you remember;"
        " end dates are exclusive, use them as < end)",
        f"this month: {_range(month, _first_of_month(today.year, today.month + 1))}",
        f"last month: {_range(_first_of_month(today.year, today.month - 1), month)}",
        f"this quarter: {_range(quarter, _first_of_month(today.year, quarter.month + 3))}",
        f"last quarter: {_range(_first_of_month(today.year, quarter.month - 3), quarter)}",
        f"this year: {_range(date(today.year, 1, 1), date(today.year + 1, 1, 1))}",
        f"last year: {_range(date(today.year - 1, 1, 1), date(today.year, 1, 1))}",
        f"this month so far: {_range(month, tomorrow)}",
        "same days last year: "
        + _range(
            _same_day_in_year(month, today.year - 1),
            last_year_today + timedelta(days=1),
        ),
    ]
    for year in (today.year, today.year - 1):
        for number, name in enumerate(MONTH_NAMES, start=1):
            start = _first_of_month(year, number)
            lines.append(f"{name} {year}: {_range(start, _first_of_month(year, number + 1))}")
    return "\n".join(lines)
