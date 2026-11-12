from retail_analyst.guardrails import mask_rows


def test_emails_and_phone_numbers_inside_strings_are_redacted():
    rows = [{"note": "write to bob@example.com or call +1 (415) 555-0132 today", "n": 3}]
    assert mask_rows(rows) == [{"note": "write to [REDACTED] or call [REDACTED] today", "n": 3}]


def test_dates_timestamps_and_plain_text_are_left_alone():
    row = {"d": "2024-01-15", "t": "2024-01-15 10:30:00", "s": "Jeans", "x": None}
    assert mask_rows([row]) == [row]


def test_values_under_blocked_column_names_are_fully_replaced():
    rows = [{"Email": "x", "last_name": "Rossi", "user_geom": 1, "city": "Rome"}]
    assert mask_rows(rows) == [
        {
            "Email": "[REDACTED]",
            "last_name": "[REDACTED]",
            "user_geom": "[REDACTED]",
            "city": "Rome",
        }
    ]


def test_input_is_not_mutated():
    rows = [{"email": "a@b.co"}]
    mask_rows(rows)
    assert rows == [{"email": "a@b.co"}]
