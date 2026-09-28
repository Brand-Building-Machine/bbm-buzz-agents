"""Bulk YouTube transcript corpus for a research question.

WHY THIS EXISTS
---------------
The research team's YouTube path used to be: yt-search (discovery) -> yt-intel
(one full grounded brief per video). yt-intel is expensive per video, so the
scout was instructed to cut to 2-5 videos. That instruction was written before
yt-intel's 2026-08-18 captions-first redesign made raw transcripts effectively
free (~4s, no model call, no length ceiling). The ration survived the reason
for it.

Two costs were being conflated:
  * reading a video  -- now ~4s and free (captions)
  * BRIEFING a video -- still expensive (yt-intel's grounded pass against
                        the owner's whole workspace). Correct to ration. Still yt-intel's
                        job, and it stays the right tool for a single link.

So this script does the first at scale and leaves the second alone.

DISCOVERY IS THE REAL BOTTLENECK
--------------------------------
yt-search runs `ytsearch{count*3}: --dump-json`, which extracts FULL metadata
one video at a time (~15-20s each, 120s budget, usually returns partial). A
measured 30-video flat discovery takes 1.9s. The difference is subscriber
counts -- needed for yt-search's views-to-subs outlier ratio, which is a
CONTENT-SELECTION metric and not a research one. We drop it and get the whole
candidate list back in seconds.

upload_date is absent from flat mode, but the caption step already needs a
full `yt-dlp -j` per video (that is where caption URLs live) and that call
carries upload_date. So the date filter moves AFTER the parallel stage and
costs nothing extra. Net: one -j per video, parallelized, doing double duty --
versus today's serial -j for discovery plus a second -j for the transcript.

EVERYTHING IS KEPT
------------------
Full timestamped transcripts are written to disk and never discarded, because
the downstream consumer is a content team that will mine this corpus later for
material this run had no reason to extract. The per-video extract is a lens
over the transcript, never a replacement for it. Timestamps are load-bearing:
fact-checker must be able to jump to the exact moment in the video to verify a
claim independently, which it cannot do against flat prose.
"""
import argparse
import concurrent.futures
import importlib.util
import json
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _load_by_path(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Everything is loaded by explicit file path, relative to THIS file: the plugin
# lives in a cache dir, the cwd is arbitrary, and both this skill and yt-intel
# ship a package literally named `scripts`, so a plain `from scripts import X`
# can resolve to the wrong skill.
paths = _load_by_path("_yt_corpus_paths", Path(__file__).resolve().parent / "paths.py")


# Reuse the proven caption path rather than duplicating it. yt-intel owns this
# logic; fetch.py loads its own paths.py by file path too.
def _load_yt_intel_fetch():
    return _load_by_path("yt_intel_fetch", paths.yt_intel_dir() / "scripts" / "fetch.py")


ytfetch = _load_yt_intel_fetch()

_FLASH = "gemini-2.5-flash"

# YouTube 429s under naive fan-out -- observed at 8 concurrent caption pulls,
# and again at 5-wide with a 2s/4s backoff (2 of 12 videos lost on a live run).
# The caption endpoint rate-limits noticeably harder than the -j metadata call,
# so the budget is spent on completeness rather than on shaving seconds: at
# these numbers the whole stage is still ~20s against the ~16min it replaces.
_DEFAULT_CONCURRENCY = 4
_MAX_RETRIES = 4
_BACKOFF_BASE = 4.0
_MAX_BACKOFF = 20.0  # 4s, 16s, 20s -- outlasts a throttle without stalling the pool

_throttle_lock = threading.Lock()
_last_call = [0.0]
_MIN_SPACING = 0.35  # seconds between outbound calls, global across threads


def _spaced():
    """Global minimum spacing between outbound calls. Cheap insurance against
    the 429 that naive ThreadPool fan-out triggers."""
    with _throttle_lock:
        delta = time.monotonic() - _last_call[0]
        if delta < _MIN_SPACING:
            time.sleep(_MIN_SPACING - delta)
        _last_call[0] = time.monotonic()


# --- discovery -----------------------------------------------------------


def _yt_dlp_cmd() -> list:
    """yt-dlp invocation that works with or without the CLI binary on PATH.

    Same fallback yt-search and yt-intel use: some environments (often Windows
    and agent sandboxes) have the yt_dlp Python module but no binary.
    """
    binary = shutil.which("yt-dlp")
    return [binary] if binary else [sys.executable, "-m", "yt_dlp"]


def discover(queries: list[str], per_query: int, runner=subprocess.run) -> list[dict]:
    """Flat search across N queries. Near-instant: no per-video extraction.
    Dedupes by video id, preserving first-seen order (so earlier queries in the
    list carry more weight, which is why the caller should order them)."""
    seen: dict[str, dict] = {}
    for q in queries:
        _spaced()
        result = runner(
            _yt_dlp_cmd() + [f"ytsearch{per_query}:{q}", "--flat-playlist", "-j", "--no-warnings"],
            capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print(f"  ! discovery failed for {q!r}: {result.stderr.strip()[:200]}", file=sys.stderr)
            continue
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = row.get("id")
            if not vid or vid in seen:
                continue
            seen[vid] = {
                "id": vid,
                "url": row.get("url") or f"https://www.youtube.com/watch?v={vid}",
                "title": row.get("title"),
                "channel": row.get("channel") or row.get("uploader"),
                "channel_id": row.get("channel_id"),
                "duration_seconds": row.get("duration"),
                "view_count": row.get("view_count"),
                "found_via": q,
            }
    return list(seen.values())


def prefilter(cands: list[dict], min_seconds: int, max_per_channel: int) -> tuple[list[dict], list[dict]]:
    """Cut before we spend any network on transcripts.

    Shorts are dropped (a 45s clip is not evidence of practice), and a single
    channel is capped so one prolific creator cannot become 'the consensus' --
    trend-analyst treats one source repeated as ONE source, so handing it ten
    videos from one channel actively wastes the run.
    """
    kept, dropped = [], []
    per_channel: dict[str, int] = {}
    for c in sorted(cands, key=lambda r: -(r.get("view_count") or 0)):
        dur = c.get("duration_seconds")
        if dur is not None and dur < min_seconds:
            dropped.append({**c, "drop_reason": f"under {min_seconds}s"})
            continue
        ch = c.get("channel_id") or c.get("channel") or "?"
        if per_channel.get(ch, 0) >= max_per_channel:
            dropped.append({**c, "drop_reason": f"channel cap {max_per_channel}"})
            continue
        per_channel[ch] = per_channel.get(ch, 0) + 1
        kept.append(c)
    return kept, dropped


# --- transcripts ---------------------------------------------------------

def json3_timestamped(raw: bytes) -> list[dict]:
    """json3 -> [{t, text}] preserving start times.

    yt-intel's _json3_to_text deliberately flattens to prose; we need the clock
    so fact-checker can verify a quote at source. Auto-captions arrive as
    rolling word-level events, so we merge events into readable lines and keep
    the FIRST start time of each line.
    """
    data = json.loads(raw)
    out: list[dict] = []
    for event in data.get("events", []):
        segs = event.get("segs") or []
        text = "".join(s.get("utf8", "") for s in segs)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        t = int((event.get("tStartMs") or 0) / 1000)
        if out and t - out[-1]["t"] < 8 and len(out[-1]["text"]) < 220:
            out[-1]["text"] = (out[-1]["text"] + " " + text).strip()
        else:
            out.append({"t": t, "text": text})
    return out


def vtt_timestamped(raw: bytes) -> list[dict]:
    """Fallback when json3 isn't offered. Dedupes YouTube's rolling repeats the
    same way yt-intel's _vtt_to_text does, but anchored to cue start times."""
    text = raw.decode("utf-8", errors="replace")
    out: list[dict] = []
    cur_t: Optional[int] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or line.isdigit():
            continue
        if "-->" in line:
            m = re.match(r"(\d+):(\d+):(\d+)", line)
            if m:
                h, mi, s = (int(x) for x in m.groups())
                cur_t = h * 3600 + mi * 60 + s
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        if out and (line in out[-1]["text"] or out[-1]["text"] in line):
            if len(line) > len(out[-1]["text"]):
                out[-1]["text"] = line
            continue
        out.append({"t": cur_t if cur_t is not None else 0, "text": line})
    return out


def fmt_date(ud) -> str:
    """yt-dlp returns YYYYMMDD; humans and downstream agents both want dashes."""
    s = str(ud or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else (s or "unknown")


def hhmmss(seconds: int) -> str:
    h, rem = divmod(max(0, int(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fetch_transcript(cand: dict) -> dict:
    """One yt-dlp -j (metadata + caption URLs) then a direct caption pull.
    Retries on 429 with exponential backoff. Never raises -- a failure is a
    recorded gap with its error text, because a silently missing video looks
    identical to a video that had nothing to say."""
    url = cand["url"]
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            _spaced()
            info = ytfetch._yt_dlp_json(url)
            meta = ytfetch._extract_metadata_fields(info)
            track = ytfetch._select_caption_track(info, lang="en")
            if track is None:
                return {**cand, **meta, "status": "no-captions",
                        "error": "no English caption track offered",
                        "lines": [], "fetch_method": None}
            _spaced()
            raw = ytfetch._fetch_url_bytes(track["url"])
            lines = json3_timestamped(raw) if track["ext"] == "json3" else vtt_timestamped(raw)
            if not lines:
                return {**cand, **meta, "status": "empty-captions",
                        "error": f"caption track parsed to zero lines ({track['ext']})",
                        "lines": [], "fetch_method": None}
            return {**cand, **meta, "status": "ok", "lines": lines,
                    "fetch_method": f"captions-{'manual' if track['manual'] else 'auto'}",
                    "caption_ext": track["ext"], "caption_lang": track["lang"]}
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            transient = "429" in str(e) or "timed out" in str(e).lower() or "temporar" in str(e).lower()
            if transient and attempt < _MAX_RETRIES - 1:
                # Jitter so a throttled batch does not retry in lockstep and
                # re-trigger the same limit together.
                # Capped: an uncapped 4**3 sleeps 64s on a video that is probably
                # doomed anyway, and it blocks a pool worker the whole time.
                delay = min(_BACKOFF_BASE ** (attempt + 1), _MAX_BACKOFF)
                time.sleep(delay * (0.7 + 0.6 * random.random()))
                continue
            break
    return {**cand, "status": "fetch-failed", "error": last_err, "lines": [], "fetch_method": None}


def within_window(rec: dict, cutoff: Optional[str]) -> bool:
    """upload_date only exists after the full -j, so this runs post-fetch.
    Undated videos are KEPT and flagged, never silently dropped."""
    if not cutoff:
        return True
    ud = rec.get("upload_date")
    if not ud:
        return True
    return str(ud) >= cutoff


# --- extraction (map) ----------------------------------------------------

_EXTRACT_SCHEMA_HINT = """Return ONLY a JSON object, no prose, no code fence:
{
  "relevant": true|false,
  "relevance_note": "one line: why this does or does not bear on the question",
  "summary": "3-4 sentences on what this video actually covers",
  "claims": [
    {"claim": "specific claim as stated",
     "evidence": "demonstrated" | "narrated" | "asserted",
     "timestamp": "H:MM:SS as it appears in the transcript",
     "quote": "verbatim quote, <=40 words"}
  ],
  "tools_named": ["concrete product/library/model names actually used"],
  "contradicts": "any claim here that conflicts with common advice, or null",
  "content_hooks": ["moments a content team could build a post around"]
}"""


def build_extract_prompt(question: str, rec: dict, transcript: str) -> str:
    return f"""You are extracting research evidence from one YouTube transcript.

RESEARCH QUESTION:
{question}

VIDEO: {rec.get('title')}
CHANNEL: {rec.get('channel')}
UPLOADED: {fmt_date(rec.get('upload_date'))}
URL: {rec.get('url')}

Rules that matter more than completeness:
- The evidence label is the single most valuable thing you produce. Three levels,
  and you are reading a TRANSCRIPT, so judge only by what the words prove:
    * "demonstrated" -- the speaker is narrating a live run and reacting to real
      output they are seeing: numbers read aloud, an error hit and handled, "that
      took about four seconds", "okay so it returned three results", "huh, that
      failed". Reacting to a REAL RESULT is the tell.
    * "narrated"     -- walkthrough language with no observed result quoted back:
      "so we add the tool here", "then you press shift-tab". They are probably
      showing something, but the transcript does not prove any of it worked.
    * "asserted"     -- a general claim with no run behind it at all: "subagents
      drain your usage limits", "this is the best way to do X".
  Do NOT mark something demonstrated because the speaker said "let me show you."
  An intention to demo is not a demo. Captions cannot see the screen, and
  over-claiming here corrupts every downstream conclusion.
- Ignore sponsor reads, ads, merch plugs, and channel promos entirely. Never list
  a sponsor's product under tools_named.
- If a product name is obviously garbled by auto-captions, write your best guess
  followed by (sic) rather than inventing a clean name.
- Every claim carries the timestamp from the transcript so it can be verified
  at source. A claim with no timestamp is worthless here -- drop it instead.
- Quote verbatim. Do not paraphrase into a quote.
- If the video does not bear on the question, say so with relevant:false and
  keep the summary short. Padding an irrelevant video is a failure.
- Do not infer what the video "probably" showed. Only what the transcript says.

{_EXTRACT_SCHEMA_HINT}

TRANSCRIPT:
{transcript}"""


def extract_one(question: str, rec: dict, transcript: str, client, model: str) -> dict:
    """One cheap flash call per video. Failure is recorded, never fabricated --
    the transcript is on disk regardless, so a failed extract costs a lens, not
    the evidence."""
    try:
        resp = client.models.generate_content(
            model=model, contents=[build_extract_prompt(question, rec, transcript)],
        )
        text = (resp.text or "").strip()
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {"status": "extract-unparseable", "raw": text[:500]}
        return {"status": "ok", **json.loads(m.group(0))}
    except json.JSONDecodeError as e:
        return {"status": "extract-unparseable", "error": str(e)}
    except Exception as e:
        return {"status": "extract-failed", "error": f"{type(e).__name__}: {e}"}


# --- persistence ---------------------------------------------------------

def transcript_markdown(rec: dict) -> str:
    """Timestamped transcript as a readable file. Front-matter carries the
    provenance every downstream consumer needs (source, date, fetch method) so
    the file stands alone if it is ever read outside the run folder."""
    head = [
        "---",
        f"video_id: {rec['id']}",
        f"title: {json.dumps(rec.get('title') or '')}",
        f"channel: {json.dumps(rec.get('channel') or '')}",
        f"url: {rec.get('url')}",
        f"upload_date: {fmt_date(rec.get('upload_date'))}",
        f"duration_seconds: {rec.get('duration_seconds')}",
        f"view_count: {rec.get('view_count')}",
        f"fetch_method: {rec.get('fetch_method')}",
        f"found_via: {json.dumps(rec.get('found_via') or '')}",
        "---",
        "",
        f"# {rec.get('title')}",
        f"\n{rec.get('channel')} · {fmt_date(rec.get('upload_date'))} · {rec.get('url')}\n",
        "## Transcript\n",
    ]
    body = [f"**[{hhmmss(l['t'])}]** {l['text']}" for l in rec.get("lines", [])]
    return "\n".join(head) + "\n".join(body) + "\n"


def write_corpus(corpus_dir: Path, records: list[dict], extracts: dict, meta: dict) -> None:
    tdir = corpus_dir / "transcripts"
    edir = corpus_dir / "extracts"
    tdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)

    manifest = {**meta, "videos": []}
    for rec in records:
        entry = {k: rec.get(k) for k in
                 ("id", "url", "title", "channel", "upload_date", "duration_seconds",
                  "view_count", "status", "fetch_method", "error", "found_via")}
        if rec.get("status") == "ok":
            tpath = tdir / f"{rec['id']}.md"
            tpath.write_text(transcript_markdown(rec), encoding="utf-8")
            entry["transcript"] = f"transcripts/{rec['id']}.md"
            entry["transcript_lines"] = len(rec.get("lines", []))
            entry["transcript_words"] = sum(len(l["text"].split()) for l in rec.get("lines", []))
            ex = extracts.get(rec["id"])
            if ex is not None:
                (edir / f"{rec['id']}.json").write_text(
                    json.dumps(ex, indent=2, ensure_ascii=False), encoding="utf-8")
                entry["extract"] = f"extracts/{rec['id']}.json"
                entry["extract_status"] = ex.get("status")
                entry["relevant"] = ex.get("relevant")
        manifest["videos"].append(entry)

    (corpus_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (corpus_dir / "INDEX.md").write_text(render_index(manifest, extracts), encoding="utf-8")


def render_index(manifest: dict, extracts: dict) -> str:
    """The file trend-analyst and the content team actually open first.

    trend-analyst has no fetch tools by design (Read/Glob/Grep only), so this
    has to be self-sufficient: every claim visible here, with its evidence
    label and timestamp, without opening anything else.
    """
    ok = [v for v in manifest["videos"] if v.get("status") == "ok"]
    rel = [v for v in ok if v.get("relevant") is not False]
    failed = [v for v in manifest["videos"] if v.get("status") != "ok"]

    out = [
        f"# YouTube corpus — {manifest.get('question')}",
        "",
        f"**Run:** {manifest.get('run_slug')} · **Built:** {manifest.get('built_at')}",
        f"**Queries:** " + "; ".join(f"`{q}`" for q in manifest.get("queries", [])),
        "",
        f"**Discovered** {manifest.get('discovered')} · "
        f"**prefilter-dropped** {manifest.get('prefilter_dropped')} · "
        f"**attempted** {manifest.get('attempted')} · "
        f"**transcribed** {len(ok)} · "
        f"**judged relevant** {len(rel)} · "
        f"**failed** {len(failed)}",
        "",
        "Full timestamped transcripts are in `transcripts/`. The extracts below are a",
        "lens over them for this question, never a replacement — a later run or a",
        "content team should read the transcript, not this summary.",
        "",
        "---",
        "",
    ]

    if failed:
        out += ["## Gaps — not in this corpus", ""]
        for v in failed:
            out.append(f"- [{v.get('status')}] [{v.get('title')}]({v.get('url')}) — {v.get('error')}")
        out.append("")

    tally = {"DEMONSTRATED": 0, "NARRATED": 0, "ASSERTED": 0}
    out += ["## Videos", ""]
    for v in sorted(rel, key=lambda r: str(r.get("upload_date") or ""), reverse=True):
        ex = extracts.get(v["id"]) or {}
        out += [
            f"### [{v.get('title')}]({v.get('url')})",
            f"`{v.get('channel')}` · {fmt_date(v.get('upload_date'))} · "
            f"{hhmmss(v.get('duration_seconds') or 0)} · {v.get('transcript_words', 0):,} words · "
            f"[transcript]({v.get('transcript')})",
            "",
        ]
        if ex.get("summary"):
            out += [ex["summary"], ""]
        claims = ex.get("claims") or []
        if claims:
            out.append("| Evidence | Claim | At |")
            out.append("|---|---|---|")
            for c in claims:
                label = str(c.get("evidence", "?")).upper()
                if label in tally:
                    tally[label] += 1
                claim = str(c.get("claim", "")).replace("|", "\\|")
                out.append(f"| {label} | {claim} | {c.get('timestamp', '?')} |")
            out.append("")
        if ex.get("tools_named"):
            out.append(f"**Tools:** {', '.join(ex['tools_named'])}\n")
        if ex.get("contradicts"):
            out.append(f"**Contradicts common advice:** {ex['contradicts']}\n")

    hooks = [(v, h) for v in rel for h in ((extracts.get(v["id"]) or {}).get("content_hooks") or [])]
    if hooks:
        out += ["---", "", "## Content hooks (for the content team, not this run)", ""]
        for v, h in hooks:
            out.append(f"- {h} — [{v.get('channel')}]({v.get('url')})")
        out.append("")

    out += [
        "---", "",
        "## Evidence weight", "",
        f"Across {len(rel)} relevant videos: "
        f"**{tally['DEMONSTRATED']} demonstrated** · "
        f"{tally['NARRATED']} narrated · {tally['ASSERTED']} asserted.",
        "",
        "Captions cannot see the screen, so `demonstrated` here means the speaker read a",
        "real result back on the audio. A video whose value is visual (a UI walkthrough, a",
        "dashboard demo) will under-report — send that one through `yt-intel --video` rather",
        "than trusting this count.",
    ]
    return "\n".join(out) + "\n"


# --- main ----------------------------------------------------------------

def main():
    # Windows: a piped stdout/stderr defaults to cp1252 and crashes on the
    # progress arrows and on emoji / non-Latin video titles. Force UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="Build a bulk YouTube transcript corpus for a research question.")
    ap.add_argument("question", help="the research question the corpus serves")
    ap.add_argument("--query", "-q", action="append", required=True,
                    help="a YouTube search query (repeatable; order = weight)")
    ap.add_argument("--per-query", type=int, default=20, help="candidates per query (default 20)")
    ap.add_argument("--max-videos", type=int, default=30, help="hard cap on transcripts (default 30)")
    ap.add_argument("--months", type=int, default=12, help="only keep videos this recent (default 12)")
    ap.add_argument("--no-date-filter", action="store_true")
    ap.add_argument("--min-seconds", type=int, default=180, help="drop shorts (default 180)")
    ap.add_argument("--max-per-channel", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=_DEFAULT_CONCURRENCY)
    ap.add_argument("--run-dir", help="research run folder; corpus goes to <run-dir>/evidence/youtube/")
    ap.add_argument("--slug", default=None, help="corpus slug when no --run-dir")
    ap.add_argument("--no-extract", action="store_true",
                    help="transcripts only, skip the per-video extraction pass")
    ap.add_argument("--model", default=_FLASH)
    args = ap.parse_args()

    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", args.question.lower())[:50].strip("-")
    if args.run_dir:
        corpus_dir = Path(args.run_dir).expanduser().resolve() / "evidence" / "youtube"
        corpus_dir.mkdir(parents=True, exist_ok=True)
    else:
        corpus_dir = paths.default_corpus_dir(slug, ytfetch.paths.data_root())

    cutoff = None
    if not args.no_date_filter:
        cutoff = (datetime.now() - timedelta(days=args.months * 30)).strftime("%Y%m%d")

    print(f"→ discovering across {len(args.query)} quer{'y' if len(args.query)==1 else 'ies'}…",
          file=sys.stderr)
    t0 = time.monotonic()
    cands = discover(args.query, args.per_query)
    print(f"  {len(cands)} unique candidates in {time.monotonic()-t0:.1f}s", file=sys.stderr)
    if not cands:
        print("No candidates found. Nothing written.", file=sys.stderr)
        return 1

    kept, dropped = prefilter(cands, args.min_seconds, args.max_per_channel)
    attempt = kept[: args.max_videos]
    print(f"  prefilter dropped {len(dropped)}; attempting {len(attempt)}", file=sys.stderr)

    print(f"→ pulling transcripts ({args.concurrency}-wide)…", file=sys.stderr)
    t1 = time.monotonic()
    records: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for rec in pool.map(fetch_transcript, attempt):
            mark = "ok" if rec["status"] == "ok" else rec["status"]
            print(f"  [{mark}] {str(rec.get('title'))[:64]}", file=sys.stderr)
            records.append(rec)

    in_window = [r for r in records if r["status"] != "ok" or within_window(r, cutoff)]
    aged_out = len(records) - len(in_window)
    records = in_window
    ok = [r for r in records if r["status"] == "ok"]
    print(f"  {len(ok)} transcripts in {time.monotonic()-t1:.1f}s "
          f"({aged_out} aged out of the {args.months}-month window)", file=sys.stderr)

    extracts: dict[str, dict] = {}
    if ok and not args.no_extract:
        key = ytfetch._load_key()
        if not key:
            print("  ! no GEMINI_API_KEY (optional; the owner's own key) — writing "
                  "transcripts without extracts", file=sys.stderr)
        else:
            from google import genai
            client = genai.Client(api_key=key)
            print(f"→ extracting against the question ({args.model})…", file=sys.stderr)
            t2 = time.monotonic()

            def _job(rec):
                text = "\n".join(f"[{hhmmss(l['t'])}] {l['text']}" for l in rec["lines"])
                return rec["id"], extract_one(args.question, rec, text, client, args.model)

            with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                for vid, ex in pool.map(_job, ok):
                    extracts[vid] = ex
                    if ex.get("status") != "ok":
                        print(f"  ! extract {ex.get('status')} for {vid}", file=sys.stderr)
            rel = sum(1 for e in extracts.values() if e.get("relevant") is not False)
            print(f"  {len(extracts)} extracts ({rel} relevant) in {time.monotonic()-t2:.1f}s",
                  file=sys.stderr)

    meta = {
        "question": args.question, "queries": args.query, "run_slug": slug,
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window_months": None if args.no_date_filter else args.months,
        "discovered": len(cands), "prefilter_dropped": len(dropped),
        "attempted": len(attempt), "aged_out": aged_out,
        "transcribed": len(ok), "total_seconds": round(time.monotonic() - t0, 1),
    }
    write_corpus(corpus_dir, records, extracts, meta)

    print(f"\n✓ corpus: {corpus_dir}", file=sys.stderr)
    print(f"  {len(ok)} transcripts · {len(extracts)} extracts · "
          f"{meta['total_seconds']}s total", file=sys.stderr)
    print(str(corpus_dir))  # stdout = the path, for the calling agent
    return 0


if __name__ == "__main__":
    sys.exit(main())
