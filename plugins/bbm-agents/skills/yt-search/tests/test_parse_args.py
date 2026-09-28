import pytest

from scripts.search import parse_args


def test_defaults():
    query, count, months, days, json_mode = parse_args(["search.py", "claude", "code"])
    assert query == "claude code"
    assert count == 20
    assert months == 6
    assert days is None
    assert json_mode is False


def test_count_months_days_flags():
    query, count, months, days, json_mode = parse_args(
        ["search.py", "AI", "agents", "--count", "5", "--months", "3", "--days", "1"]
    )
    assert query == "AI agents"
    assert count == 5
    assert months == 3
    assert days == 1  # --days overrides --months downstream, both are still parsed


def test_no_date_filter_zeroes_months():
    _, _, months, days, _ = parse_args(["search.py", "topic", "--no-date-filter"])
    assert months == 0
    assert days is None


def test_json_flag():
    query, _, _, _, json_mode = parse_args(["search.py", "topic", "--json"])
    assert query == "topic"
    assert json_mode is True


def test_json_flag_order_independent():
    query, count, _, _, json_mode = parse_args(
        ["search.py", "--json", "--count", "3", "topic", "here"]
    )
    assert json_mode is True
    assert count == 3
    assert query == "topic here"


def test_missing_query_exits_with_usage():
    with pytest.raises(SystemExit) as exc:
        parse_args(["search.py", "--count", "5"])
    assert exc.value.code == 1


def test_bad_count_exits():
    with pytest.raises(SystemExit) as exc:
        parse_args(["search.py", "topic", "--count", "notanumber"])
    assert exc.value.code == 1
