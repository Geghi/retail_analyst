from datetime import date, timedelta


def last_complete_month(today: date) -> tuple[date, date]:
    end = today.replace(day=1)
    start = (end - timedelta(days=1)).replace(day=1)
    return start, end


def churn_cutoff(today: date, days: int = 90) -> date:
    return today - timedelta(days=days)
