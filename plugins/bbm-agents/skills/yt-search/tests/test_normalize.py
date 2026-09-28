from scripts.search import normalize_video, format_subscribers, format_views, format_duration, format_date, iso_date


RAW_VIDEO = {
    "id": "abc123",
    "title": "How AI Agents Actually Work",
    "channel": "Some Channel",
    "uploader": "Some Channel Uploader",
    "view_count": 246000,
    "channel_follower_count": 100000,
    "duration": 754,
    "upload_date": "20260810",
}


def test_normalize_video_computes_ratio_and_urls():
    v = normalize_video(RAW_VIDEO)
    assert v["id"] == "abc123"
    assert v["url"] == "https://youtube.com/watch?v=abc123"
    assert v["title"] == "How AI Agents Actually Work"
    assert v["channel"] == "Some Channel"
    assert v["subscribers"] == 100000
    assert v["views"] == 246000
    assert v["views_per_subscriber"] == 2.46
    assert v["views_per_subscriber_display"] == "2.46x"
    assert v["duration_seconds"] == 754
    assert v["duration_display"] == "12:34"
    assert v["upload_date"] == "2026-08-10"
    assert v["upload_date_display"] == "Aug 10, 2026"


def test_normalize_video_falls_back_to_uploader_when_no_channel():
    v = normalize_video({"id": "x", "uploader": "Fallback Name"})
    assert v["channel"] == "Fallback Name"


def test_normalize_video_missing_id_has_no_url():
    v = normalize_video({"title": "No ID Video"})
    assert v["id"] is None
    assert v["url"] is None


def test_normalize_video_missing_subs_or_views_yields_null_ratio():
    v = normalize_video({"id": "x", "view_count": 1000, "channel_follower_count": None})
    assert v["subscribers"] is None
    assert v["views_per_subscriber"] is None
    assert v["views_per_subscriber_display"] == "N/A"


def test_normalize_video_zero_subscribers_yields_null_ratio():
    v = normalize_video({"id": "x", "view_count": 1000, "channel_follower_count": 0})
    assert v["views_per_subscriber"] is None


def test_normalize_video_missing_duration():
    v = normalize_video({"id": "x"})
    assert v["duration_seconds"] is None
    assert v["duration_display"] == "N/A"


def test_normalize_video_prefers_duration_string():
    v = normalize_video({"id": "x", "duration": 90, "duration_string": "1:30"})
    assert v["duration_display"] == "1:30"


def test_normalize_video_missing_upload_date():
    v = normalize_video({"id": "x"})
    assert v["upload_date"] is None
    assert v["upload_date_display"] == "N/A"


# --- format_* unit coverage (used both standalone and inside normalize_video) ---

def test_format_subscribers_scales():
    assert format_subscribers(None) == "N/A"
    assert format_subscribers(500) == "500"
    assert format_subscribers(45200) == "45.2K"
    assert format_subscribers(1200000) == "1.2M"


def test_format_views_commas():
    assert format_views(None) == "N/A"
    assert format_views(1234567) == "1,234,567"


def test_format_duration_hours():
    assert format_duration({"duration": 3725}) == "1:02:05"


def test_format_date_invalid_length():
    assert format_date("2026") == "N/A"


def test_iso_date_invalid_length():
    assert iso_date("2026") is None


def test_iso_date_valid():
    assert iso_date("20260101") == "2026-01-01"
