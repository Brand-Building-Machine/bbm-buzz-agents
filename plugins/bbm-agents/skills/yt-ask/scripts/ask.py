#!/usr/bin/env python3
"""Pull one YouTube video's transcript so the caller can answer a specific question about it.

This is the thin sibling of `yt-intel`. yt-intel always writes the same standard brief;
this one answers whatever the owner actually asked. It deliberately does NOT call a model to
produce the answer -- it fetches the grounding material and hands it to the agent that
invoked it, which then answers in its own voice with the transcript in context. One model
hop, not two, and nothing is summarized before the agent sees it.

Transcript acquisition is entirely yt-intel's `fetch.py`: captions first, Gemini video/audio
fallback routed by duration. This script owns no fetching logic of its own, so a fix there
is a fix here.

Usage (run by path; works from any working directory):
    python "<yt-ask skill dir>/scripts/ask.py" "<url>" "<question>" [--deep] [--video]
                                              [--json] [--max-chars N]
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_own_paths():
    """Load this skill's paths.py by file path (see yt-intel's fetch.py for why)."""
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("_yt_ask_paths", here / "paths.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths = _load_own_paths()


def _load_yt_intel_fetch():
    """Load yt-intel's fetch.py by path.

    Both skills ship a package literally named `scripts`, so a plain
    `from scripts import fetch` resolves to yt-ask's own package and fails.
    Load the module from its file instead. fetch.py in turn loads its own
    paths.py by file path, so nothing depends on sys.path or the cwd.
    """
    intel = paths.yt_intel_dir()
    spec = importlib.util.spec_from_file_location(
        "yt_intel_fetch", intel / "scripts" / "fetch.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ytfetch = _load_yt_intel_fetch()

DEFAULT_MAX_CHARS = 400_000
TRUNCATION_NOTE = (
    "\n\n[... {dropped:,} characters omitted from the middle of this transcript "
    "({kept:,} of {total:,} kept: the opening and the ending). The omitted middle was NOT "
    "read. Do not claim the video does or does not cover something on the strength of this "
    "truncated text -- say the middle was not read. Re-run with a larger --max-chars to "
    "close the gap. ...]\n\n"
)


def truncate_middle(text: str, max_chars: int) -> tuple[str, dict]:
    """Keep the head and tail, drop the middle, and say so loudly.

    Head and tail beat a plain head cut: a video's framing is at the front and its
    conclusions are at the back, and a question is as likely to be about either.
    """
    total = len(text)
    if max_chars <= 0 or total <= max_chars:
        return text, {"truncated": False, "total_chars": total, "kept_chars": total, "dropped_chars": 0}

    # Reserve room for the note itself so the result actually fits the budget.
    note_budget = len(TRUNCATION_NOTE.format(dropped=total, kept=total, total=total))
    body = max(max_chars - note_budget, 0)
    if body <= 0:
        return text, {"truncated": False, "total_chars": total, "kept_chars": total, "dropped_chars": 0}

    head_len = body // 2
    tail_len = body - head_len
    dropped = total - body
    note = TRUNCATION_NOTE.format(dropped=dropped, kept=body, total=total)
    out = text[:head_len] + note + text[total - tail_len:]
    return out, {"truncated": True, "total_chars": total, "kept_chars": body, "dropped_chars": dropped}


def build_payload(url: str, question: str, *, deep=False, force_video=False,
                  max_chars=DEFAULT_MAX_CHARS, fetcher=None) -> dict:
    fetcher = fetcher or ytfetch.fetch
    result = fetcher(url, deep=deep, force_video=force_video)

    if result.get("error"):
        return {"status": "error", "question": question, "url": url,
                "error": result["error"], "transcript": None, "metadata": {}}

    transcript = result.get("transcript")
    if not transcript:
        return {
            "status": "no_transcript", "question": question,
            "url": result.get("url", url), "video_id": result.get("video_id"),
            "metadata": result.get("metadata", {}),
            "error": result.get("last_error") or result.get("caption_fallback_reason")
                     or "no transcript could be obtained",
            "transcript": None,
        }

    text, trunc = truncate_middle(transcript, max_chars)
    return {
        "status": "ok", "question": question,
        "url": result.get("url", url), "video_id": result.get("video_id"),
        "metadata": result.get("metadata", {}),
        "fetch_method": result.get("fetch_method"),
        "caption_lang": result.get("caption_lang"),
        "model": result.get("model"),
        "transcript": text, "transcript_chars": trunc,
        "error": None,
    }


def _fmt_duration(seconds) -> str:
    if not seconds:
        return "unknown"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def render(payload: dict) -> str:
    meta = payload.get("metadata") or {}
    title = meta.get("title") or "(title unavailable)"
    channel = meta.get("channel") or "(channel unavailable)"

    if payload["status"] == "error":
        return f"FETCH FAILED for {payload['url']}\n{payload['error']}\n\nDo not answer the question. Report this failure."

    header = [
        f"VIDEO:    {title}",
        f"CHANNEL:  {channel}",
        f"DURATION: {_fmt_duration(meta.get('duration_seconds'))}",
        f"URL:      {payload['url']}",
    ]

    if payload["status"] == "no_transcript":
        header.append("")
        header.append(f"NO TRANSCRIPT: {payload['error']}")
        header.append("")
        header.append("Metadata only. Answer from the title and channel if that genuinely "
                      "suffices, otherwise say the transcript could not be retrieved. Do not "
                      "guess at the contents.")
        return "\n".join(header)

    method = payload.get("fetch_method") or "unknown"
    if payload.get("caption_lang"):
        method += f" ({payload['caption_lang']})"
    header.append(f"SOURCE:   {method}")

    tc = payload.get("transcript_chars") or {}
    if tc.get("truncated"):
        header.append(f"NOTE:     transcript truncated -- {tc['kept_chars']:,} of "
                      f"{tc['total_chars']:,} chars kept (head + tail)")

    return "\n".join([
        *header, "",
        "QUESTION:", payload["question"], "",
        "Answer the question above using only the transcript below. Quote it where it helps.",
        "If the transcript does not answer the question, say exactly that -- do not fill the",
        "gap from general knowledge about the topic or the channel.", "",
        "--- TRANSCRIPT ---", payload["transcript"], "--- END TRANSCRIPT ---",
    ])


def main():
    # Windows: a piped stdout defaults to cp1252 and crashes on emoji titles.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Fetch a YouTube transcript to answer a specific question about it.")
    ap.add_argument("url")
    ap.add_argument("question", help="the question to answer about this video")
    ap.add_argument("--deep", action="store_true", help="thorough transcription pass")
    ap.add_argument("--video", action="store_true", help="skip captions, force the video/audio path")
    ap.add_argument("--json", action="store_true", help="emit the payload as JSON instead of formatted text")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help=f"truncate the transcript above this length (default {DEFAULT_MAX_CHARS:,}; 0 disables)")
    args = ap.parse_args()

    payload = build_payload(args.url, args.question, deep=args.deep,
                            force_video=args.video, max_chars=args.max_chars)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render(payload))

    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
