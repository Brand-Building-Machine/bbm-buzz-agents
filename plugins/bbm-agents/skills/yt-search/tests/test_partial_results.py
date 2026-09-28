import json

from scripts.search import collect_results, evaluate_results, build_payload, TIMEOUT_SECONDS


def _line(video_id, upload_date="20260801"):
    return json.dumps({"id": video_id, "title": video_id, "upload_date": upload_date})


def _clock(values):
    """A now_fn stub that returns each value in sequence, one call per line examined."""
    it = iter(values)
    return lambda: next(it)


def test_collect_results_times_out_before_reaching_count():
    lines = [_line("a"), _line("b"), _line("c")]
    # deadline already exceeded by the time the first line finishes processing
    videos, skipped, timed_out = collect_results(
        lines, cutoff=None, count=10, deadline=100, now_fn=_clock([150, 999, 999])
    )
    assert timed_out is True
    assert len(videos) == 1


def test_collect_results_not_timed_out_when_count_reached_first():
    lines = [_line("a"), _line("b")]
    videos, skipped, timed_out = collect_results(
        lines, cutoff=None, count=2, deadline=100, now_fn=_clock([10, 20, 30])
    )
    assert timed_out is False
    assert len(videos) == 2


def test_evaluate_results_ok():
    outcome = evaluate_results(
        video_count=5, skipped=0, timed_out=False, cutoff=None, period_label="6 months",
        proc_returncode=0, stderr_text="",
    )
    assert outcome["status"] == "ok"
    assert outcome["exit_code"] == 0
    assert outcome["error"] is None


def test_evaluate_results_partial_when_timed_out_with_results():
    outcome = evaluate_results(
        video_count=3, skipped=0, timed_out=True, cutoff="20260101", period_label="6 months",
        proc_returncode=None, stderr_text="",
    )
    assert outcome["status"] == "partial"
    assert outcome["exit_code"] == 0
    assert any(str(TIMEOUT_SECONDS) in note for note in outcome["notes"])
    assert any("partial result" in note for note in outcome["notes"])


def test_evaluate_results_empty_timeout_no_hits():
    outcome = evaluate_results(
        video_count=0, skipped=0, timed_out=True, cutoff=None, period_label="",
        proc_returncode=None, stderr_text="",
    )
    assert outcome["status"] == "empty"
    assert outcome["exit_code"] == 0
    assert any(str(TIMEOUT_SECONDS) in note for note in outcome["notes"])


def test_evaluate_results_empty_no_results_at_all():
    outcome = evaluate_results(
        video_count=0, skipped=0, timed_out=False, cutoff=None, period_label="",
        proc_returncode=0, stderr_text="",
    )
    assert outcome["status"] == "empty"
    assert outcome["notes"] == ["No results found."]


def test_evaluate_results_empty_after_date_filtering():
    outcome = evaluate_results(
        video_count=0, skipped=4, timed_out=False, cutoff="20260101", period_label="1 day",
        proc_returncode=0, stderr_text="",
    )
    assert outcome["status"] == "empty"
    assert any("Filtered out 4" in note for note in outcome["notes"])
    assert any("within the last 1 day" in note for note in outcome["notes"])


def test_evaluate_results_error_when_ytdlp_fails_outright():
    outcome = evaluate_results(
        video_count=0, skipped=0, timed_out=False, cutoff=None, period_label="",
        proc_returncode=1, stderr_text="boom: no such option",
    )
    assert outcome["status"] == "error"
    assert outcome["exit_code"] == 1
    assert outcome["error"] == "boom: no such option"


def test_evaluate_results_timeout_takes_precedence_over_error_branch():
    # Even with a nonzero returncode, a timeout (not a real failure) should not
    # report as "error" — it's a truthful empty/partial result under budget.
    outcome = evaluate_results(
        video_count=0, skipped=0, timed_out=True, cutoff=None, period_label="",
        proc_returncode=1, stderr_text="terminated",
    )
    assert outcome["status"] == "empty"


def test_build_payload_surfaces_partial_status_and_metadata():
    videos_raw = [{"id": "a", "title": "A", "upload_date": "20260801"}]
    payload = build_payload(
        query="ai agents", requested_count=5, months=6, days=None,
        cutoff="20260101", period_label="6 months", videos_raw=videos_raw,
        skipped=2, timed_out=True, status="partial", error=None,
    )
    assert payload["status"] == "partial"
    assert payload["timed_out"] is True
    assert payload["timeout_seconds"] == TIMEOUT_SECONDS
    assert payload["skipped_older_than_window"] == 2
    assert payload["result_count"] == 1
    assert payload["query"] == "ai agents"
    assert payload["window"]["cutoff_date"] == "2026-01-01"
    assert payload["window"]["no_date_filter"] is False
