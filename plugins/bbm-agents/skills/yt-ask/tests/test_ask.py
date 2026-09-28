import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
from scripts import ask  # noqa: E402


def _fetch_ok(transcript="the speaker explains how to wire the agent to a relay", **meta):
    def _f(url, *, deep=False, force_video=False):
        return {
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "metadata": {"title": "Wiring agents", "channel": "Some Channel",
                         "duration_seconds": 754, **meta},
            "fetch_method": "captions-manual", "caption_lang": "en", "model": None,
            "transcript": transcript, "transcript_available": True,
            "error": None, "last_error": None,
        }
    return _f


# --- truncate_middle ------------------------------------------------------

def test_short_transcript_is_untouched():
    text, info = ask.truncate_middle("short", 1000)
    assert text == "short"
    assert info == {"truncated": False, "total_chars": 5, "kept_chars": 5, "dropped_chars": 0}


def test_zero_max_chars_disables_truncation():
    body = "x" * 5000
    text, info = ask.truncate_middle(body, 0)
    assert text == body
    assert info["truncated"] is False


def test_truncation_keeps_head_and_tail():
    body = "A" * 2000 + "B" * 2000
    text, info = ask.truncate_middle(body, 1000)
    assert info["truncated"] is True
    assert text.startswith("A")
    assert text.rstrip().endswith("B")
    assert "omitted from the middle" in text


def test_truncation_accounting_is_exact():
    body = "z" * 10_000
    _, info = ask.truncate_middle(body, 2_000)
    assert info["total_chars"] == 10_000
    assert info["kept_chars"] + info["dropped_chars"] == info["total_chars"]


def test_truncated_output_respects_the_budget():
    body = "q" * 50_000
    text, _ = ask.truncate_middle(body, 3_000)
    assert len(text) <= 3_000


def test_budget_too_small_for_the_note_returns_full_text():
    """Better to hand back everything than to emit a note with no transcript around it."""
    body = "m" * 5_000
    text, info = ask.truncate_middle(body, 10)
    assert text == body
    assert info["truncated"] is False


# --- build_payload --------------------------------------------------------

def test_payload_ok():
    p = ask.build_payload("https://youtu.be/abc123", "how does it connect?", fetcher=_fetch_ok())
    assert p["status"] == "ok"
    assert p["question"] == "how does it connect?"
    assert p["metadata"]["title"] == "Wiring agents"
    assert p["fetch_method"] == "captions-manual"
    assert p["error"] is None


def test_payload_surfaces_fetch_error():
    def _f(url, **kw):
        return {"error": "could not extract a video ID from 'nonsense'"}
    p = ask.build_payload("nonsense", "q", fetcher=_f)
    assert p["status"] == "error"
    assert p["transcript"] is None
    assert "could not extract" in p["error"]


def test_payload_distinguishes_missing_transcript_from_error():
    def _f(url, **kw):
        return {"video_id": "x", "url": "u", "metadata": {"title": "T"},
                "transcript": None, "last_error": "gemini quota exhausted"}
    p = ask.build_payload("u", "q", fetcher=_f)
    assert p["status"] == "no_transcript"
    assert p["error"] == "gemini quota exhausted"


def test_no_transcript_falls_back_to_caption_reason():
    def _f(url, **kw):
        return {"video_id": "x", "url": "u", "metadata": {}, "transcript": None,
                "last_error": None, "caption_fallback_reason": "no caption track published"}
    p = ask.build_payload("u", "q", fetcher=_f)
    assert p["status"] == "no_transcript"
    assert p["error"] == "no caption track published"


def test_payload_truncates_long_transcripts():
    p = ask.build_payload("u", "q", max_chars=1_000, fetcher=_fetch_ok("y" * 20_000))
    assert p["transcript_chars"]["truncated"] is True
    assert len(p["transcript"]) <= 1_000


def test_flags_are_passed_through_to_the_fetcher():
    seen = {}

    def _f(url, *, deep=False, force_video=False):
        seen.update(deep=deep, force_video=force_video)
        return _fetch_ok()(url)

    ask.build_payload("u", "q", deep=True, force_video=True, fetcher=_f)
    assert seen == {"deep": True, "force_video": True}


# --- render ---------------------------------------------------------------

def test_render_includes_question_transcript_and_grounding_instruction():
    out = ask.render(ask.build_payload("u", "what did they say about relays?", fetcher=_fetch_ok()))
    assert "what did they say about relays?" in out
    assert "--- TRANSCRIPT ---" in out
    assert "Wiring agents" in out
    assert "do not fill the" in out


def test_render_error_tells_the_caller_not_to_answer():
    out = ask.render({"status": "error", "url": "u", "error": "boom", "metadata": {}})
    assert "Do not answer the question" in out


def test_render_no_transcript_warns_against_guessing():
    p = ask.build_payload("u", "q", fetcher=lambda url, **kw: {
        "video_id": "x", "url": "u", "metadata": {"title": "T", "channel": "C"},
        "transcript": None, "last_error": "no captions"})
    out = ask.render(p)
    assert "NO TRANSCRIPT" in out
    assert "Do not guess" in out
    assert "--- TRANSCRIPT ---" not in out


def test_render_surfaces_truncation_to_the_reader():
    p = ask.build_payload("u", "q", max_chars=1_200, fetcher=_fetch_ok("w" * 40_000))
    assert "truncated" in ask.render(p)


@pytest.mark.parametrize("seconds,expected", [
    (None, "unknown"), (0, "unknown"), (45, "0:45"), (754, "12:34"), (8664, "2:24:24"),
])
def test_duration_formatting(seconds, expected):
    assert ask._fmt_duration(seconds) == expected
