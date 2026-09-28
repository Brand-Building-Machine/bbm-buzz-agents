"""Fetch one YouTube video's metadata + transcript for yt-intel.

Metadata comes from yt-dlp (-j, no download).

Transcript, in priority order (2026-08-18 redesign -- see the SKILL.md
change log for the "why"):

  1. YouTube captions (via yt-dlp's caption URLs, fetched directly) -- free,
     instant, no model call, no length ceiling. This is the path for almost
     every video. Manual captions preferred over auto-generated when both
     exist; json3 (structured, cleanest to parse) preferred over vtt.
  2. Gemini video/audio understanding -- ONLY when no caption track exists
     at all, or the caller explicitly asks for it (`--video`, meant for the
     rare case where step 3's judgment pass finds the caption transcript is
     missing load-bearing on-screen content). Duration-routed across three
     methods (video-default / video-low / audio-extract) to stay under
     Gemini's 1,048,576-token input ceiling on long videos, with a
     ceiling-error escalation net on top of the duration guess.

This was NOT the original design. Gemini video/audio transcription was the
ONLY path until 2026-08-18, when a real 2h24m11s video 400'd on both
flash and pro. The first fix (duration-routed media resolution + audio
fallback, still below) solved the 400, but testing it for real surfaced a
second, worse failure: even once the input ceiling was avoided, Gemini's
video-understanding call on a 2h24m video returned only ~12 minutes of
actual transcript followed by its own meta-commentary about "creating a
plan before transcribing the rest" -- an output-side failure with no error
code, which would have silently produced a garbage brief. Captions have
neither failure mode, so they're now the default and Gemini video/audio
understanding is the fallback, not the reverse.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional


def _load_own_paths():
    """Load this skill's paths.py by file path, relative to THIS file.

    Sibling skills (yt-ask, yt-corpus) also ship a package literally named
    `scripts`, and they load this module by file path. A plain
    `from scripts import paths` could then resolve to THEIR paths module.
    Loading by __file__ works from any install location and any cwd.
    """
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("_yt_intel_paths", here / "paths.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths = _load_own_paths()

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

_FLASH = "gemini-2.5-flash"
_PRO = "gemini-2.5-pro"

# Google's documented ceilings for a 1M-context model are "up to 1 hour" at
# default resolution and "up to 3 hours" at low resolution (Gemini API video
# understanding docs, checked 2026-08-18). These thresholds sit a buffer
# under each. Only reachable now via the no-captions/--video fallback.
_DEFAULT_SAFE_SECONDS = 50 * 60  # 3000s
_LOW_RES_SAFE_SECONDS = 165 * 60  # 9900s

_TOKEN_CEILING_SNIPPET = "exceeds the maximum number of tokens"

_ID_RES = [
    re.compile(r"(?:v=|/shorts/|youtu\.be/|/embed/)([\w-]{11})"),
]


class GeminiCallError(Exception):
    """A Gemini call failed with a real, surfaced reason -- never silently
    swallowed to a generic 'unavailable'."""

    def __init__(self, message: str, *, token_ceiling: bool = False):
        super().__init__(message)
        self.token_ceiling = token_ceiling


def extract_video_id(url: str) -> str | None:
    for rx in _ID_RES:
        m = rx.search(url)
        if m:
            return m.group(1)
    return None


def _load_key(env_path=None) -> str | None:
    """The owner's OWN Gemini key -- optional, never bundled with this skill.

    Looked up in the GEMINI_API_KEY environment variable first, then (as a
    convenience) in a `.env` file: `env_path` if given, else `.env` in the
    current working directory if one happens to exist. Returns None when no
    key is configured; the captions path never needs one.
    """
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip() or None
    envf = Path(env_path) if env_path is not None else Path.cwd() / ".env"
    if envf.is_file():
        for raw in envf.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


# --- Metadata + caption discovery (one yt-dlp -j call feeds both) ---------


def _yt_dlp_cmd() -> list:
    """yt-dlp invocation that works with or without the CLI binary on PATH.

    Some environments have the binary on PATH, others only have the Python
    module installed (common on Windows and inside agent sandboxes). Prefer the
    binary, fall back to the module so the skill runs identically either way.
    """
    binary = shutil.which("yt-dlp")
    return [binary] if binary else [sys.executable, "-m", "yt_dlp"]


def _yt_dlp_json(video_url: str, runner=subprocess.run) -> dict:
    result = runner(
        _yt_dlp_cmd() + ["-j", "--no-download", "--no-warnings", video_url],
        capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()[:500]}")
    return json.loads(result.stdout)


def _extract_metadata_fields(data: dict) -> dict:
    return {
        "title": data.get("title"),
        "channel": data.get("channel") or data.get("uploader"),
        "upload_date": data.get("upload_date"),
        "duration_seconds": data.get("duration"),
        "view_count": data.get("view_count"),
        "description": (data.get("description") or "")[:1000],
    }


def get_metadata(video_url: str, runner=subprocess.run) -> dict:
    """yt-dlp -j, no download. Raises on failure so the caller can report it plainly."""
    return _extract_metadata_fields(_yt_dlp_json(video_url, runner))


def _select_caption_track(info: dict, lang: str = "en") -> Optional[dict]:
    """Manual captions before auto-generated; json3 (structured) before vtt.
    Returns {"url", "ext", "manual", "lang"} or None if nothing usable."""
    for manual, key in ((True, "subtitles"), (False, "automatic_captions")):
        tracks = info.get(key) or {}
        for candidate_lang in (lang, f"{lang}-US", f"{lang}-orig"):
            fmts = tracks.get(candidate_lang)
            if not fmts:
                continue
            fmt = (next((f for f in fmts if f.get("ext") == "json3"), None)
                   or next((f for f in fmts if f.get("ext") == "vtt"), None))
            if fmt and fmt.get("url"):
                return {"url": fmt["url"], "ext": fmt["ext"], "manual": manual, "lang": candidate_lang}
    return None


def _fetch_url_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as resp:
        return resp.read()


def _json3_to_text(raw: bytes) -> str:
    """YouTube's json3 caption format: word-level events with segs, plus
    bare '\\n' events marking rolling-caption line breaks. Concatenate in
    order and collapse the line-break markers into paragraph breaks."""
    data = json.loads(raw)
    parts = [seg.get("utf8", "") for event in data.get("events", [])
              for seg in (event.get("segs") or [])]
    text = "".join(parts)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def _vtt_to_text(raw: bytes) -> str:
    """Fallback parser for vtt (only used when json3 isn't offered). Strips
    cue index/timing lines and inline <...> tags, then dedupes the rolling-
    caption repeats YouTube's auto-vtt sends (each line re-sent as one more
    word is added) by keeping the longest version of overlapping lines."""
    text = raw.decode("utf-8", errors="replace")
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        if lines and (line in lines[-1] or lines[-1] in line):
            if len(line) > len(lines[-1]):
                lines[-1] = line
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def get_captions(info: dict, lang: str = "en") -> tuple[Optional[str], Optional[dict]]:
    """Returns (text, track_info) on success, (None, track_or_None) on
    failure -- track_info carries an 'error' key when a track existed but
    couldn't be turned into usable text, so the caller always knows why."""
    track = _select_caption_track(info, lang=lang)
    if track is None:
        return None, None
    try:
        raw = _fetch_url_bytes(track["url"])
        parser = _json3_to_text if track["ext"] == "json3" else _vtt_to_text
        text = parser(raw)
    except Exception as e:
        return None, {**track, "error": f"{type(e).__name__}: {e}"}
    if not text:
        return None, {**track, "error": "caption track fetched but parsed empty"}
    return text, track


# --- Gemini video/audio fallback (rare path -- see module docstring) ------

def _prompt_for(kind: str) -> str:
    noun = "recording" if kind == "audio" else "video"
    return (
        f"Transcribe this {noun} into clean, readable text that captures everything the "
        "speaker teaches or claims: every tool, technique, step, opinion, and recommendation, "
        "in order. Do not editorialize or summarize -- this is a transcript, not a summary. "
        "If you cannot access the content, reply with exactly: NO_ACCESS"
    )


def _client(api_key: str):
    from google import genai
    from google.genai import types
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=20 * 60 * 1000))


def _raise_from_api_error(e) -> None:
    from google.genai import errors
    if isinstance(e, errors.APIError):
        msg = f"HTTP {e.code}: {e.message or e}"
        ceiling = bool(e.message) and _TOKEN_CEILING_SNIPPET in e.message
        raise GeminiCallError(msg, token_ceiling=ceiling) from e
    raise GeminiCallError(f"{type(e).__name__}: {e}") from e


def _video_transcript(client, canonical_url: str, model: str, low_res: bool) -> str:
    from google.genai import types
    part = types.Part.from_uri(file_uri=canonical_url, mime_type="video/*")
    config = types.GenerateContentConfig(
        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW
    ) if low_res else None
    try:
        resp = client.models.generate_content(
            model=model, contents=[part, _prompt_for("video")], config=config,
        )
    except Exception as e:
        _raise_from_api_error(e)
    return resp.text or ""


def _extract_audio(canonical_url: str, video_id: str, runner=subprocess.run) -> Path:
    out_dir = paths.tmp_dir() / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = out_dir / f"{video_id}.%(ext)s"
    result = runner(
        _yt_dlp_cmd() + ["-x", "--audio-format", "mp3", "--audio-quality", "5",
                         "--no-warnings", "-o", str(out_template), canonical_url],
        capture_output=True, text=True, timeout=1800,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp audio extraction failed: {result.stderr.strip()[:500]}")
    out_path = out_dir / f"{video_id}.mp3"
    if not out_path.exists():
        raise RuntimeError(f"yt-dlp reported success but {out_path} is missing")
    return out_path


def _audio_transcript(client, audio_path: Path, model: str) -> str:
    import time
    media = client.files.upload(file=str(audio_path))
    waited = 0
    while media.state.name == "PROCESSING":
        time.sleep(3)
        waited += 3
        media = client.files.get(name=media.name)
        if waited > 600:
            raise GeminiCallError("Gemini file processing did not finish within 10 minutes")
    if media.state.name == "FAILED":
        raise GeminiCallError("Gemini failed to process the uploaded audio (corrupt/unsupported)")
    try:
        resp = client.models.generate_content(
            model=model, contents=[media, _prompt_for("audio")],
        )
    except Exception as e:
        _raise_from_api_error(e)
    finally:
        try:
            client.files.delete(name=media.name)
        except Exception:
            pass
    return resp.text or ""


def _route_method(duration_seconds: Optional[int]) -> str:
    if duration_seconds is None:
        return "video-default"
    if duration_seconds <= _DEFAULT_SAFE_SECONDS:
        return "video-default"
    if duration_seconds <= _LOW_RES_SAFE_SECONDS:
        return "video-low"
    return "audio"


def _escalate_method(method: str) -> Optional[str]:
    return {"video-default": "video-low", "video-low": "audio"}.get(method)


def _attempt(method: str, canonical_url: str, video_id: str, client, model: str):
    """One real Gemini attempt. Returns (transcript_or_None,
    error_message_or_None, token_ceiling_bool). Never swallows an exception
    without recording what it was."""
    audio_path = None
    try:
        if method == "audio":
            audio_path = _extract_audio(canonical_url, video_id)
            text = _audio_transcript(client, audio_path, model)
        else:
            text = _video_transcript(client, canonical_url, model, low_res=(method == "video-low"))
    except GeminiCallError as e:
        return None, str(e), e.token_ceiling
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", False
    finally:
        if audio_path is not None:
            audio_path.unlink(missing_ok=True)

    text = (text or "").strip()
    if not text:
        return None, "empty response from Gemini", False
    if text == "NO_ACCESS":
        return None, "Gemini reported NO_ACCESS (private/age-restricted/region-locked)", False
    return text, None, False


def _gemini_fallback(canonical_url: str, video_id: str, duration, deep: bool) -> dict:
    """The full duration-routed video/audio path -- only reached when
    captions aren't usable. Returns the video/audio-specific fields to
    merge into the result dict."""
    model = _PRO if deep else _FLASH
    method = _route_method(duration)
    attempts: list[dict] = []

    api_key = _load_key()
    if not api_key:
        return {
            "model": model, "fetch_method": method, "retried_on_pro": False,
            "attempts": attempts, "transcript": None, "transcript_available": False,
            "last_error": ("no caption track and no GEMINI_API_KEY configured -- the optional "
                           "Gemini fallback needs the owner's own key in the GEMINI_API_KEY "
                           "environment variable"),
        }

    client = _client(api_key)
    transcript, err, ceiling = _attempt(method, canonical_url, video_id, client, model)
    attempts.append({"method": method, "model": model, "error": err})

    # Ceiling-error escalation net: if the real response 400s on token
    # count regardless of what the duration predicted, step down to the
    # next cheaper method rather than just failing.
    while transcript is None and ceiling:
        next_method = _escalate_method(method)
        if not next_method:
            break
        method = next_method
        transcript, err, ceiling = _attempt(method, canonical_url, video_id, client, model)
        attempts.append({"method": method, "model": model, "error": err})

    # Transient-failure retry -- one extra attempt on the same method,
    # always ending on pro. Fixes the old bug where --deep (which starts on
    # pro) never got a second attempt at all.
    retried_on_pro = False
    if transcript is None and not ceiling:
        retried_on_pro = True
        model = _PRO
        transcript, err, ceiling = _attempt(method, canonical_url, video_id, client, model)
        attempts.append({"method": method, "model": model, "error": err})

    return {
        "model": model, "fetch_method": method, "retried_on_pro": retried_on_pro,
        "attempts": attempts, "transcript": transcript,
        "transcript_available": transcript is not None, "last_error": err,
    }


def fetch(video_url: str, *, deep: bool = False, force_video: bool = False) -> dict:
    video_id = extract_video_id(video_url)
    if not video_id:
        return {"error": f"could not extract a video ID from {video_url!r}"}

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        info = _yt_dlp_json(canonical_url)
        meta = _extract_metadata_fields(info)
        meta_error = None
    except Exception as e:
        info = {}
        meta = {}
        meta_error = str(e)

    base = {
        "video_id": video_id, "url": canonical_url, "deep": deep,
        "metadata": meta, "metadata_error": meta_error,
    }

    caption_fallback_reason = None
    if not force_video:
        caption_text, track = get_captions(info)
        if caption_text:
            return {
                **base,
                "model": None,
                "fetch_method": "captions-manual" if track["manual"] else "captions-auto",
                "caption_lang": track.get("lang"),
                "retried_on_pro": False,
                "attempts": [],
                "transcript": caption_text,
                "transcript_available": True,
                "last_error": None,
                "caption_fallback_reason": None,
            }
        caption_fallback_reason = (track or {}).get("error") if track else (
            "no caption track published for this video"
        )
    else:
        caption_fallback_reason = "skipped -- caller requested the video/audio path directly (--video)"

    gemini_result = _gemini_fallback(canonical_url, video_id, meta.get("duration_seconds"), deep)
    return {**base, **gemini_result, "caption_fallback_reason": caption_fallback_reason}


def _utf8_stdio():
    """Agents run this with stdout piped. On Windows a piped stdout defaults to
    the ANSI code page (cp1252), which crashes on emoji / non-Latin titles.
    Force UTF-8 with replacement. Called from main() only, never at import."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _utf8_stdio()
    ap = argparse.ArgumentParser(description="Fetch metadata + transcript for one YouTube video.")
    ap.add_argument("url", help="YouTube video URL (watch, youtu.be, or shorts)")
    ap.add_argument("--deep", action="store_true",
                     help="if the Gemini fallback runs, use gemini-2.5-pro for a harder pass")
    ap.add_argument("--video", action="store_true", dest="force_video",
                     help="skip captions and go straight to the Gemini video/audio path "
                          "(use when a caption-derived transcript was judged to be missing "
                          "load-bearing on-screen content)")
    ap.add_argument("--out-dir", default=None,
                     help="where to write {video_id}.json (default: the per-user data dir; "
                          "see paths.py / YT_SKILLS_DATA_DIR)")
    args = ap.parse_args()

    result = fetch(args.url, deep=args.deep, force_video=args.force_video)
    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else paths.tmp_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{result['video_id']}.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    title = (result["metadata"] or {}).get("title", "(title unavailable)")
    print(f"{title}")
    print(f"  video_id: {result['video_id']}")
    print(f"  metadata: {'OK' if not result['metadata_error'] else 'FAILED: ' + result['metadata_error']}")
    print(f"  fetch_method: {result['fetch_method']}")
    if result.get("caption_fallback_reason"):
        print(f"  caption fallback reason: {result['caption_fallback_reason']}")
    retry_note = " [retried once more]" if result.get("retried_on_pro") else ""
    if result["transcript_available"]:
        model_note = f", {result['model']}" if result.get("model") else ""
        print(f"  transcript: OK ({len(result['transcript'])} chars{model_note}, "
              f"{result['fetch_method']}){retry_note}")
    else:
        print(f"  transcript: UNAVAILABLE after {len(result['attempts'])} attempt(s)")
        for a in result["attempts"]:
            print(f"    - {a['method']} / {a['model']}: {a['error']}")
    print(f"  -> {out_path}")
    if not result["transcript_available"]:
        print(f"\nNo transcript available. Last error: {result['last_error']}")
        sys.exit(2)


if __name__ == "__main__":
    main()
