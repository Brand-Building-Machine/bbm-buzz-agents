import json

from scripts.search import build_payload, render_table


VIDEOS_RAW = [
    {
        "id": "abc123",
        "title": "How AI Agents Actually Work",
        "channel": "Some Channel",
        "view_count": 246000,
        "channel_follower_count": 100000,
        "duration": 754,
        "upload_date": "20260810",
    },
    {
        "id": "def456",
        "title": "No Subs Data",
        "uploader": "Uploader Only",
        "view_count": 500,
        "channel_follower_count": None,
        "duration": None,
        "upload_date": "",
    },
]

REQUIRED_VIDEO_FIELDS = {
    "id", "url", "title", "channel", "subscribers", "views",
    "views_per_subscriber", "duration_seconds", "duration_display", "upload_date",
}

REQUIRED_TOP_LEVEL_FIELDS = {
    "query", "requested_count", "window", "status", "timed_out",
    "timeout_seconds", "skipped_older_than_window", "result_count",
    "videos", "error",
}


def _payload(**overrides):
    kwargs = dict(
        query="ai agents", requested_count=5, months=6, days=None,
        cutoff="20260101", period_label="6 months", videos_raw=VIDEOS_RAW,
        skipped=1, timed_out=False, status="ok", error=None,
    )
    kwargs.update(overrides)
    return build_payload(**kwargs)


def test_payload_top_level_contract_fields_present():
    payload = _payload()
    assert REQUIRED_TOP_LEVEL_FIELDS.issubset(payload.keys())


def test_payload_video_fields_present_for_every_video():
    payload = _payload()
    for v in payload["videos"]:
        assert REQUIRED_VIDEO_FIELDS.issubset(v.keys())


def test_payload_is_json_serializable_round_trips():
    payload = _payload()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded == payload


def test_payload_window_metadata():
    payload = _payload(months=3, days=None, cutoff="20260601", period_label="3 months")
    assert payload["window"]["months"] == 3
    assert payload["window"]["days"] is None
    assert payload["window"]["cutoff_date"] == "2026-06-01"
    assert payload["window"]["period_label"] == "3 months"
    assert payload["window"]["no_date_filter"] is False


def test_payload_no_date_filter_true_when_no_cutoff():
    payload = _payload(cutoff=None, period_label="")
    assert payload["window"]["no_date_filter"] is True
    assert payload["window"]["cutoff_date"] is None


def test_payload_result_count_matches_normalized_video_count():
    payload = _payload()
    assert payload["result_count"] == len(payload["videos"]) == 2


def test_payload_error_status_carries_message_and_empty_videos():
    payload = _payload(videos_raw=[], status="error", error="yt-dlp not found")
    assert payload["status"] == "error"
    assert payload["error"] == "yt-dlp not found"
    assert payload["videos"] == []


def test_render_table_uses_normalized_fields():
    payload = _payload()
    table = render_table(payload["videos"])
    assert "How AI Agents Actually Work" in table
    assert "https://youtube.com/watch?v=abc123" in table
    assert "2.46x" in table
    # second video has no ratio -> no Engagement line for it, but title present
    assert "No Subs Data" in table
