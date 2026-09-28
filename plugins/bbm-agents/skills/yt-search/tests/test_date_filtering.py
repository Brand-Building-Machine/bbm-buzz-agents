import json
from datetime import datetime, timedelta

from scripts.search import (
    get_cutoff_date,
    describe_period,
    compute_fetch_count,
    collect_results,
)


def _line(video_id, upload_date):
    return json.dumps({"id": video_id, "title": video_id, "upload_date": upload_date})


def test_get_cutoff_date_days_overrides_months():
    cutoff = get_cutoff_date(months=6, days=1)
    expected = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    assert cutoff == expected


def test_get_cutoff_date_no_filter_when_months_zero_and_no_days():
    assert get_cutoff_date(months=0, days=None) is None


def test_get_cutoff_date_zero_or_negative_days_disables_filter():
    assert get_cutoff_date(months=6, days=0) is None
    assert get_cutoff_date(months=6, days=-3) is None


def test_describe_period_labels():
    assert describe_period(months=6, days=None) == "6 months"
    assert describe_period(months=0, days=1) == "1 day"
    assert describe_period(months=0, days=3) == "3 days"
    assert describe_period(months=0, days=None) == ""


def test_compute_fetch_count_scales_by_filter_type():
    assert compute_fetch_count(count=10, months=6, days=None) == 20
    assert compute_fetch_count(count=10, months=0, days=1) == 30
    assert compute_fetch_count(count=10, months=0, days=None) == 10


def test_collect_results_filters_out_older_than_cutoff():
    lines = [
        _line("old", "20200101"),
        _line("new1", "20260801"),
        _line("new2", "20260802"),
    ]
    videos, skipped, timed_out = collect_results(
        lines, cutoff="20260101", count=10, deadline=float("inf")
    )
    assert [v["id"] for v in videos] == ["new1", "new2"]
    assert skipped == 1
    assert timed_out is False


def test_collect_results_no_cutoff_keeps_everything():
    lines = [_line("a", "20200101"), _line("b", "20260101")]
    videos, skipped, timed_out = collect_results(
        lines, cutoff=None, count=10, deadline=float("inf")
    )
    assert len(videos) == 2
    assert skipped == 0


def test_collect_results_stops_early_once_count_reached():
    lines = [_line(f"v{i}", "20260801") for i in range(10)]
    videos, skipped, timed_out = collect_results(
        lines, cutoff=None, count=3, deadline=float("inf")
    )
    assert len(videos) == 3
    assert timed_out is False


def test_collect_results_skips_malformed_json_lines():
    lines = ["not json", _line("ok", "20260801")]
    videos, skipped, timed_out = collect_results(
        lines, cutoff=None, count=10, deadline=float("inf")
    )
    assert [v["id"] for v in videos] == ["ok"]
