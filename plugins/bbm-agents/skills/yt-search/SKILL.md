---
name: yt-search
tier: tool
status: beta
category: Content / YouTube
description: Search YouTube and return structured video results with engagement metrics (views, subs, and a views-to-subscribers outlier ratio that flags videos punching above their channel size). Use whenever the user wants to search YouTube, find videos on a topic, research what's trending, compare videos, or look up creators/channels. Triggers on "search YouTube for", "find videos about", "what videos are there on", "YouTube results for", or any YouTube video discovery/research. Adapted from the Chase AI research pack (MIT).
---

# YouTube Search

Search YouTube via `yt-dlp` and return structured, formatted results with engagement metrics. No API key — runs locally.

## How to use

This skill is installed from a plugin, so its files are not in the owner's workspace or
the current working directory. Run the script by its path relative to **this skill's own
directory** (the folder containing this `SKILL.md`), substituting the real absolute path
and keeping it quoted. On Windows use `python` (or `py`); on macOS/Linux use `python3` if
`python` is not found. Any working directory is fine.

```bash
python "<this skill's dir>/scripts/search.py" <query> [--count N] [--months N] [--days N] [--no-date-filter] [--json]
```

### Parameters
- `<query>` — search terms (required)
- `--count N` — number of results to return (default: 20)
- `--months N` — only show videos from the last N months (default: 6)
- `--days N` — only show videos from the last N days (overrides `--months`; use for "what's new today")
- `--no-date-filter` — include videos of any age
- `--json` — emit one JSON object on stdout instead of the formatted table (for downstream agents/scripts)

### Examples

```bash
# Basic search (top 20, last 6 months)
python "<this skill's dir>/scripts/search.py" claude code tutorial

# Fewer results, shorter window
python "<this skill's dir>/scripts/search.py" obsidian workflow --count 5 --months 3

# Last 24 hours (for daily scans)
python "<this skill's dir>/scripts/search.py" "AI agents" --count 10 --days 1

# All time, no date filter
python "<this skill's dir>/scripts/search.py" AI agents --count 10 --no-date-filter
```

## Output format

**Human mode (default):** each result includes title · channel + subscriber count · view count · duration · upload date · **engagement ratio (views ÷ subscribers** — higher means the video outperformed its channel's base, i.e. an outlier worth studying) · direct URL. Status messages go to stderr; the formatted table goes to stdout.

**`--json` mode:** status messages still go to stderr; stdout is a single JSON object:

```json
{
  "query": "ai agents", "requested_count": 5,
  "window": {"months": 6, "days": null, "no_date_filter": false, "cutoff_date": "2026-02-26", "period_label": "6 months"},
  "status": "ok",
  "timed_out": false, "timeout_seconds": 120,
  "skipped_older_than_window": 3, "result_count": 5,
  "videos": [
    {"id": "abc123", "url": "https://youtube.com/watch?v=abc123", "title": "...", "channel": "...",
     "subscribers": 100000, "subscribers_display": "100.0K",
     "views": 246000, "views_display": "246,000",
     "views_per_subscriber": 2.46, "views_per_subscriber_display": "2.46x",
     "duration_seconds": 754, "duration_display": "12:34",
     "upload_date": "2026-08-10", "upload_date_display": "Aug 10, 2026"}
  ],
  "error": null
}
```

`status: "partial"` means the 120s extraction budget was hit but some in-window results were still returned; `status: "empty"` is a truthful zero-result search (possibly also timed out — check `timed_out`); `status: "error"` means yt-dlp itself failed (`error` carries the message), distinct from "ran fine, found nothing."

## Notes

- Requires `yt-dlp` (`python -m pip install -U yt-dlp`; keep it updated, YouTube changes often break old versions). The script resolves it portably: it uses the `yt-dlp` binary if on PATH, otherwise falls back to `python -m yt_dlp` with the same interpreter (so it works even when pip `--user` installs it off-PATH). No API key needed.
- Fetches 2–3× the requested count to compensate for date filtering.
- **Streaming + time budget:** yt-dlp extracts full metadata one video at a time, and broad single-word queries (e.g. "Anthropic") can run ~15–20s/video. The script streams results, stops early once it has `--count` in-window hits, and otherwise returns **partial results** at a `TIMEOUT_SECONDS` budget (120s) rather than hard-failing. So a slow query may take the full ~120s and report "No results within the last N days" — that's a real, truthful empty result, not a crash. (Pre-2026-06-22 the script used a blocking `subprocess.run(timeout=120)` that discarded all output on timeout and exited with an error; that's fixed.)
- Subscriber counts come from yt-dlp metadata and may occasionally be `N/A`.
- Sibling skills: `yt-corpus` (bulk transcripts for a research question), `yt-intel` (one-video brief), `yt-ask` (one question about one video).
