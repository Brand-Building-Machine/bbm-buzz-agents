import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import fetch


def test_extract_video_id_watch_url():
    assert fetch.extract_video_id("https://www.youtube.com/watch?v=O_z9vDLgvoY") == "O_z9vDLgvoY"


def test_extract_video_id_short_url():
    assert fetch.extract_video_id("https://youtu.be/O_z9vDLgvoY") == "O_z9vDLgvoY"


def test_extract_video_id_shorts_url():
    assert fetch.extract_video_id("https://www.youtube.com/shorts/O_z9vDLgvoY") == "O_z9vDLgvoY"


def test_extract_video_id_no_match():
    assert fetch.extract_video_id("https://example.com/not-youtube") is None


# Real URL shapes people paste from a phone (9-video test batch, 2026-08-17) --
# mobile domain, shorts with a query param, and a shared timestamp param. All must
# resolve to the same 11-char ID regardless of domain/query noise.
def test_extract_video_id_mobile_watch_url():
    assert fetch.extract_video_id("https://m.youtube.com/watch?v=nm1G1zvs78M") == "nm1G1zvs78M"


def test_extract_video_id_mobile_shorts_with_query():
    assert fetch.extract_video_id("https://m.youtube.com/shorts/Fj8DKMbdIzU?ra=m") == "Fj8DKMbdIzU"


def test_extract_video_id_mobile_watch_with_timestamp():
    # &t=5s must not leak into the captured ID or break the match.
    assert fetch.extract_video_id("https://m.youtube.com/watch?v=A8l4Rw6R92A&t=5s") == "A8l4Rw6R92A"


def test_get_metadata_parses_yt_dlp_json():
    fake_stdout = json.dumps({
        "title": "Test Video", "channel": "Test Channel", "upload_date": "20260101",
        "duration": 120, "view_count": 42, "description": "a short description",
    })

    def fake_runner(cmd, capture_output, text, timeout, **kwargs):
        return SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    meta = fetch.get_metadata("https://www.youtube.com/watch?v=x", runner=fake_runner)
    assert meta["title"] == "Test Video"
    assert meta["channel"] == "Test Channel"
    assert meta["duration_seconds"] == 120


def test_get_metadata_raises_on_yt_dlp_failure():
    def fake_runner(cmd, capture_output, text, timeout, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="ERROR: video unavailable")

    try:
        fetch.get_metadata("https://www.youtube.com/watch?v=x", runner=fake_runner)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "video unavailable" in str(e)


# --- Duration-based routing (2026-08-18 long-video fix) ------------------
# Real boundary that motivated this: a 2h24m11s (8651s) video 400'd on both
# flash and pro at default resolution. Google's docs say default resolution
# is good for "up to 1 hour," low resolution for "up to 3 hours" on a 1M-
# token model -- these tests lock in the buffered thresholds derived from
# that, not just restate the constants.

def test_route_method_unknown_duration_starts_cheap():
    assert fetch._route_method(None) == "video-default"


def test_route_method_short_video_stays_default():
    assert fetch._route_method(48 * 60) == "video-default"  # the prior working max


def test_route_method_the_actual_failing_video_routes_to_low_res():
    assert fetch._route_method(8651) == "video-low"  # 2h24m11s, a real video that 400'd


def test_route_method_just_over_default_threshold_goes_low():
    assert fetch._route_method(fetch._DEFAULT_SAFE_SECONDS + 1) == "video-low"


def test_route_method_very_long_video_goes_straight_to_audio():
    assert fetch._route_method(fetch._LOW_RES_SAFE_SECONDS + 1) == "audio"


def test_escalate_method_chain():
    assert fetch._escalate_method("video-default") == "video-low"
    assert fetch._escalate_method("video-low") == "audio"
    assert fetch._escalate_method("audio") is None


# --- captions: the canonical, primary path (Gemini is the fallback) ------
# These have had zero direct coverage even though this is now the path almost every video
# takes -- yt-ask and yt-corpus load this same fetch.py rather than duplicating it,
# so its correctness matters beyond just yt-intel.

def test_select_caption_track_prefers_manual_over_auto():
    info = {
        "automatic_captions": {"en": [{"ext": "json3", "url": "auto"}]},
        "subtitles": {"en": [{"ext": "json3", "url": "manual"}]},
    }
    track = fetch._select_caption_track(info)
    assert track == {"url": "manual", "ext": "json3", "manual": True, "lang": "en"}


def test_select_caption_track_prefers_json3_over_vtt():
    info = {"subtitles": {"en": [
        {"ext": "vtt", "url": "v"}, {"ext": "json3", "url": "j"},
    ]}}
    track = fetch._select_caption_track(info)
    assert track["ext"] == "json3" and track["url"] == "j"


def test_select_caption_track_falls_back_to_vtt_when_no_json3():
    info = {"subtitles": {"en": [{"ext": "vtt", "url": "v"}]}}
    track = fetch._select_caption_track(info)
    assert track["ext"] == "vtt"


def test_select_caption_track_returns_none_when_no_tracks():
    assert fetch._select_caption_track({}) is None


def test_json3_to_text_concatenates_segs_and_collapses_linebreaks():
    raw = json.dumps({"events": [
        {"segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
        {"segs": [{"utf8": "\n"}]},
        {"segs": [{"utf8": "Second line"}]},
    ]}).encode()
    assert fetch._json3_to_text(raw) == "Hello world\nSecond line"


def test_vtt_to_text_strips_timing_and_tags_and_dedupes_rolling_captions():
    raw = (
        "WEBVTT\n\n"
        "1\n00:00:00.000 --> 00:00:02.000\n<c>Hello</c>\n\n"
        "2\n00:00:02.000 --> 00:00:04.000\nHello world\n\n"
    ).encode()
    # the rolling second cue supersedes the first (longer, overlapping) -- no duplicate line
    assert fetch._vtt_to_text(raw) == "Hello world"


def test_get_captions_returns_none_when_track_fetch_raises(monkeypatch):
    info = {"subtitles": {"en": [{"ext": "json3", "url": "https://x"}]}}
    monkeypatch.setattr(fetch, "_fetch_url_bytes", lambda url: (_ for _ in ()).throw(RuntimeError("boom")))
    text, track = fetch.get_captions(info)
    assert text is None
    assert track["error"] == "RuntimeError: boom"


def test_get_captions_returns_none_when_parsed_text_is_empty(monkeypatch):
    info = {"subtitles": {"en": [{"ext": "json3", "url": "https://x"}]}}
    monkeypatch.setattr(fetch, "_fetch_url_bytes", lambda url: json.dumps({"events": []}).encode())
    text, track = fetch.get_captions(info)
    assert text is None
    assert track["error"] == "caption track fetched but parsed empty"


def test_get_captions_returns_text_on_success(monkeypatch):
    info = {"subtitles": {"en": [{"ext": "json3", "url": "https://x"}]}}
    monkeypatch.setattr(fetch, "_fetch_url_bytes",
                        lambda url: json.dumps({"events": [{"segs": [{"utf8": "hi"}]}]}).encode())
    text, track = fetch.get_captions(info)
    assert text == "hi"
    assert track["manual"] is True


def test_fetch_uses_captions_when_available_and_never_calls_gemini(monkeypatch):
    # The core Outcome-1 contract: captions short-circuit fetch() entirely -- no Gemini call,
    # no duration routing, regardless of video length.
    monkeypatch.setattr(fetch, "_yt_dlp_json", lambda url, runner=None: {"duration": 999999})
    monkeypatch.setattr(fetch, "get_captions",
                        lambda info, lang="en": ("caption text", {"manual": True, "lang": "en"}))
    called = []
    monkeypatch.setattr(fetch, "_gemini_fallback", lambda *a, **k: called.append(1))

    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["transcript"] == "caption text"
    assert result["fetch_method"] == "captions-manual"
    assert called == []


def test_fetch_force_video_skips_captions_even_when_available(monkeypatch):
    monkeypatch.setattr(fetch, "_yt_dlp_json", lambda url, runner=None: {"duration": 600})
    monkeypatch.setattr(fetch, "get_captions",
                        lambda info, lang="en": ("caption text", {"manual": True, "lang": "en"}))
    monkeypatch.setattr(fetch, "_load_key", lambda env_path=None: "fake-key")
    monkeypatch.setattr(fetch, "_client", lambda api_key: object())
    monkeypatch.setattr(fetch, "_attempt", lambda *a, **k: ("gemini text", None, False))

    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa", force_video=True)
    assert result["transcript"] == "gemini text"
    assert result["caption_fallback_reason"] == (
        "skipped -- caller requested the video/audio path directly (--video)"
    )


# --- _attempt: one real call, error surfaced not swallowed ----------------

def test_attempt_video_success(monkeypatch):
    monkeypatch.setattr(fetch, "_video_transcript", lambda client, url, model, low_res: "  clean text  ")
    text, err, ceiling = fetch._attempt("video-default", "https://y/x", "vid", object(), fetch._FLASH)
    assert text == "clean text"
    assert err is None
    assert ceiling is False


def test_attempt_no_access_returns_none_with_reason(monkeypatch):
    monkeypatch.setattr(fetch, "_video_transcript", lambda *a, **k: "NO_ACCESS")
    text, err, ceiling = fetch._attempt("video-default", "https://y/x", "vid", object(), fetch._FLASH)
    assert text is None
    assert "NO_ACCESS" in err or "private" in err
    assert ceiling is False


def test_attempt_empty_response_is_a_real_reason_not_silence(monkeypatch):
    monkeypatch.setattr(fetch, "_video_transcript", lambda *a, **k: "")
    text, err, ceiling = fetch._attempt("video-default", "https://y/x", "vid", object(), fetch._FLASH)
    assert text is None
    assert "empty" in err


def test_attempt_surfaces_real_error_not_swallowed(monkeypatch):
    # This is the exact bug: a 400 used to vanish into a generic "unavailable."
    # The real message must now come through on the error.
    def fake(*a, **k):
        raise fetch.GeminiCallError(
            "HTTP 400: The input token count exceeds the maximum number of tokens allowed 1048576",
            token_ceiling=True,
        )
    monkeypatch.setattr(fetch, "_video_transcript", fake)
    text, err, ceiling = fetch._attempt("video-default", "https://y/x", "vid", object(), fetch._FLASH)
    assert text is None
    assert "exceeds the maximum number of tokens" in err
    assert ceiling is True


def test_attempt_wraps_unexpected_exception_with_real_detail(monkeypatch):
    def fake(*a, **k):
        raise TimeoutError("upstream took too long")
    monkeypatch.setattr(fetch, "_video_transcript", fake)
    text, err, ceiling = fetch._attempt("video-default", "https://y/x", "vid", object(), fetch._FLASH)
    assert text is None
    assert "upstream took too long" in err
    assert ceiling is False


def test_attempt_audio_cleans_up_local_file_even_on_failure(monkeypatch, tmp_path):
    audio_file = tmp_path / "vid.mp3"
    audio_file.write_bytes(b"fake mp3 bytes")
    monkeypatch.setattr(fetch, "_extract_audio", lambda url, vid, runner=None: audio_file)

    def fake_audio_transcript(client, path, model):
        assert path == audio_file
        raise RuntimeError("upload failed")
    monkeypatch.setattr(fetch, "_audio_transcript", fake_audio_transcript)

    text, err, ceiling = fetch._attempt("audio", "https://y/x", "vid", object(), fetch._FLASH)
    assert text is None
    assert "upload failed" in err
    assert not audio_file.exists()  # cleaned up despite the failure


# --- fetch(): orchestration, routing, escalation, retry --------------------

def _patch_common(monkeypatch, duration_seconds):
    # fetch() reads metadata via `_yt_dlp_json` directly (not the standalone `get_metadata`
    # helper) and always tries captions before Gemini -- both must be patched, or these tests
    # silently fall through to a real yt-dlp/network call and a real caption-first result
    # instead of exercising the duration-routed Gemini fallback they're actually testing.
    monkeypatch.setattr(fetch, "_yt_dlp_json", lambda url, runner=None: {"duration": duration_seconds})
    monkeypatch.setattr(fetch, "get_captions", lambda info, lang="en": (None, None))
    monkeypatch.setattr(fetch, "_load_key", lambda env_path=None: "fake-key")
    monkeypatch.setattr(fetch, "_client", lambda api_key: object())


def test_fetch_short_video_uses_video_default(monkeypatch):
    _patch_common(monkeypatch, 600)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append((method, model))
        return "transcript text", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["fetch_method"] == "video-default"
    assert calls == [("video-default", fetch._FLASH)]


def test_fetch_the_actual_failing_video_routes_to_video_low_preemptively(monkeypatch):
    # A real 2h24m11s video -- should never even attempt video-default.
    _patch_common(monkeypatch, 8651)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(method)
        return "transcript text", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=5p-sq8v3OXw")
    assert result["fetch_method"] == "video-low"
    assert calls == ["video-low"]


def test_fetch_very_long_video_routes_straight_to_audio(monkeypatch):
    _patch_common(monkeypatch, 4 * 3600)  # 4 hours
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(method)
        return "transcript text", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["fetch_method"] == "audio"
    assert calls == ["audio"]


def test_fetch_escalates_through_all_three_methods_on_repeated_ceiling(monkeypatch):
    # Short video (would normally stay on video-default) but every method
    # hits the real token ceiling -- must climb the whole ladder rather than
    # give up after one method, and each attempt's real error is preserved.
    _patch_common(monkeypatch, 600)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(method)
        if method == "audio":
            return "finally worked", None, False
        return None, f"HTTP 400: ceiling on {method}", True

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert calls == ["video-default", "video-low", "audio"]
    assert result["fetch_method"] == "audio"
    assert result["transcript"] == "finally worked"
    assert [a["error"] for a in result["attempts"][:2]] == [
        "HTTP 400: ceiling on video-default", "HTTP 400: ceiling on video-low",
    ]


def test_fetch_retries_once_on_pro_when_flash_fails_transiently(monkeypatch):
    # Original working behavior, preserved: a non-ceiling failure on flash
    # gets one retry, escalated to pro.
    _patch_common(monkeypatch, 600)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(model)
        if model == fetch._FLASH:
            return None, "transient network blip", False
        return "pro succeeded", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["transcript"] == "pro succeeded"
    assert result["retried_on_pro"] is True
    assert result["model"] == fetch._PRO
    assert calls == [fetch._FLASH, fetch._PRO]


def test_fetch_deep_mode_now_actually_gets_a_retry(monkeypatch):
    # THE BUG: --deep starts on pro, so the old "retry only if model==FLASH"
    # check meant deep runs never got a second attempt at all. Now a
    # transient failure on pro gets one more pro attempt.
    _patch_common(monkeypatch, 600)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(model)
        if len(calls) == 1:
            return None, "transient network blip", False
        return "pro succeeded on retry", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa", deep=True)
    assert result["transcript"] == "pro succeeded on retry"
    assert result["retried_on_pro"] is True
    assert calls == [fetch._PRO, fetch._PRO]  # TWO real Gemini calls, not one
    assert len(result["attempts"]) == 2


def test_fetch_no_retry_when_first_attempt_succeeds(monkeypatch):
    _patch_common(monkeypatch, 600)
    calls = []

    def fake_attempt(method, url, vid, client, model):
        calls.append(model)
        return "flash succeeded", None, False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["retried_on_pro"] is False
    assert calls == [fetch._FLASH]  # no wasted pro call when flash already worked


def test_fetch_surfaces_the_real_final_error_not_a_generic_unavailable(monkeypatch):
    # THE BUG: fetch.py used to swallow every failure into "UNAVAILABLE
    # (tried flash + pro)" with no detail. last_error must now carry the
    # actual message from the last real attempt.
    _patch_common(monkeypatch, 600)

    def fake_attempt(method, url, vid, client, model):
        if method == "video-default":
            return None, "HTTP 400: The input token count exceeds the maximum number of tokens allowed 1048576", True
        if method == "video-low":
            return None, "HTTP 400: still too many tokens", True
        return None, "HTTP 500: Gemini file processing failed on the audio upload", False

    monkeypatch.setattr(fetch, "_attempt", fake_attempt)
    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["transcript_available"] is False
    assert "Gemini file processing failed" in result["last_error"]
    assert result["last_error"] != "UNAVAILABLE (tried flash + pro)"


def test_fetch_no_api_key_reports_clearly_without_calling_gemini(monkeypatch):
    monkeypatch.setattr(fetch, "_yt_dlp_json", lambda url, runner=None: {"duration": 600})
    monkeypatch.setattr(fetch, "get_captions", lambda info, lang="en": (None, None))
    monkeypatch.setattr(fetch, "_load_key", lambda env_path=None: None)
    called = []
    monkeypatch.setattr(fetch, "_attempt", lambda *a, **k: called.append(1))

    result = fetch.fetch("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert result["transcript_available"] is False
    assert "GEMINI_API_KEY" in result["last_error"]
    assert called == []  # no Gemini call attempted at all without a key
    assert result["attempts"] == []
