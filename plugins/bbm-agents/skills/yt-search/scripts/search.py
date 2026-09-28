#!/usr/bin/env python3
"""YouTube search via yt-dlp with structured output and views/subs ratio.

Two output modes, same underlying collection/normalization:
- human (default): formatted table on stdout, status notes on stderr.
- --json: one JSON object on stdout (query/window metadata, partial/timeout
  status, normalized video fields). Status notes still go to stderr.
"""

import io
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta

# Wall-clock budget for extraction. yt-dlp resolves full per-video metadata one
# video at a time, and for some queries (broad single words like "Anthropic")
# that is ~15-20s/video — so a 30-video batch can run for minutes. We stream
# results and stop at this budget with PARTIAL results rather than discarding
# everything on a hard timeout.
TIMEOUT_SECONDS = 120


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv):
    """Parse query, --count N, --months N, --days N, --no-date-filter, --json from argv."""
    args = argv[1:]
    count = 20
    months = 6
    days = None  # If set, overrides months
    json_mode = False
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--count" and i + 1 < len(args):
            try:
                count = int(args[i + 1])
            except ValueError:
                print(f"Error: --count requires an integer, got '{args[i + 1]}'", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--months" and i + 1 < len(args):
            try:
                months = int(args[i + 1])
            except ValueError:
                print(f"Error: --months requires an integer, got '{args[i + 1]}'", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                print(f"Error: --days requires an integer, got '{args[i + 1]}'", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--no-date-filter":
            months = 0
            i += 1
        elif args[i] == "--json":
            json_mode = True
            i += 1
        else:
            query_parts.append(args[i])
            i += 1
    query = " ".join(query_parts)
    if not query:
        print("Usage: search.py <query> [--count N] [--months N] [--days N] [--no-date-filter] [--json]", file=sys.stderr)
        print("Example: search.py claude code tutorial --count 5 --days 1", file=sys.stderr)
        sys.exit(1)
    return query, count, months, days, json_mode


# ---------------------------------------------------------------------------
# Formatting helpers (pure)
# ---------------------------------------------------------------------------

def format_subscribers(n):
    """Format subscriber count as human-readable (e.g., 45.2K, 1.2M)."""
    if n is None:
        return "N/A"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_views(n):
    """Format view count with commas."""
    if n is None:
        return "N/A"
    return f"{n:,}"


def format_duration(info):
    """Extract human-readable duration from yt-dlp info."""
    if info.get("duration_string"):
        return info["duration_string"]
    dur = info.get("duration")
    if dur is None:
        return "N/A"
    dur = int(dur)
    hours, remainder = divmod(dur, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_date(raw):
    """Convert YYYYMMDD to human-readable date (e.g., Jan 10, 2026)."""
    if not raw or len(raw) != 8:
        return "N/A"
    try:
        dt = datetime.strptime(raw, "%Y%m%d")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def iso_date(raw):
    """Convert YYYYMMDD to ISO 8601 (YYYY-MM-DD), or None if unavailable/invalid."""
    if not raw or len(raw) != 8:
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def describe_period(months, days):
    """Human label for the active date window, e.g. '6 months', '1 day', or '' (no filter)."""
    if days is not None:
        return f"{days} day{'s' if days != 1 else ''}"
    if months > 0:
        return f"{months} months"
    return ""


def get_cutoff_date(months, days=None):
    """Get the cutoff date as YYYYMMDD string. --days overrides --months."""
    if days is not None:
        if days <= 0:
            return None
        cutoff = datetime.now() - timedelta(days=days)
        return cutoff.strftime("%Y%m%d")
    if months <= 0:
        return None
    cutoff = datetime.now() - timedelta(days=months * 30)
    return cutoff.strftime("%Y%m%d")


def compute_fetch_count(count, months, days):
    """How many results to request from yt-dlp to compensate for date filtering."""
    if days is not None:
        return count * 3
    if months > 0:
        return count * 2
    return count


# ---------------------------------------------------------------------------
# yt-dlp process plumbing
# ---------------------------------------------------------------------------

def resolve_ytdlp():
    """Return the yt-dlp invocation prefix, preferring the PATH binary.

    Falls back to `<this python> -m yt_dlp` (pip --user installs often land
    off-PATH, especially on Windows and macOS). Raises RuntimeError if neither
    is available.
    """
    binary = shutil.which("yt-dlp")
    if binary:
        return [binary]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                        capture_output=True, check=True)
        return [sys.executable, "-m", "yt_dlp"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Error: yt-dlp not found. Install with: python -m pip install -U yt-dlp")


def build_search_cmd(ytdlp, search_query):
    return [
        *ytdlp,
        search_query,
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--quiet",
    ]


# ---------------------------------------------------------------------------
# Collection (network-free — takes any iterable of raw yt-dlp JSON lines)
# ---------------------------------------------------------------------------

def collect_results(line_iter, cutoff, count, deadline, now_fn=time.monotonic):
    """Consume yt-dlp --dump-json lines, filtering by cutoff and stopping early.

    Stops the moment `count` in-window videos are collected, or once `now_fn()`
    passes `deadline` (the 120s partial-results safeguard) — whichever comes
    first. Takes a plain iterable of strings so it can be tested with a list
    of JSON lines instead of a live subprocess.

    Returns (videos: list[dict], skipped: int, timed_out: bool).
    """
    videos = []
    skipped = 0
    timed_out = False
    for line in line_iter:
        line = line.strip()
        if line:
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                info = None
            if info is not None:
                if cutoff and (info.get("upload_date") or "00000000") < cutoff:
                    skipped += 1
                else:
                    videos.append(info)
                    if len(videos) >= count:
                        break  # got enough in-window results — stop early
        if now_fn() > deadline:
            timed_out = True
            break
    return videos, skipped, timed_out


# ---------------------------------------------------------------------------
# Normalization (pure — one raw yt-dlp info dict -> the downstream contract)
# ---------------------------------------------------------------------------

def normalize_video(info):
    """Normalize one yt-dlp info dict into the stable fields downstream agents use."""
    title = info.get("title", "Unknown Title")
    channel = info.get("channel", info.get("uploader", "Unknown"))
    views = info.get("view_count")
    subs = info.get("channel_follower_count")
    duration = info.get("duration")
    duration_seconds = int(duration) if duration is not None else None
    video_id = info.get("id") or None
    url = f"https://youtube.com/watch?v={video_id}" if video_id else None
    upload_date_raw = info.get("upload_date", "")

    ratio = views / subs if (subs and views and subs > 0) else None

    return {
        "id": video_id,
        "url": url,
        "title": title,
        "channel": channel,
        "subscribers": subs,
        "subscribers_display": format_subscribers(subs),
        "views": views,
        "views_display": format_views(views),
        "views_per_subscriber": round(ratio, 4) if ratio is not None else None,
        "views_per_subscriber_display": f"{ratio:.2f}x" if ratio is not None else "N/A",
        "duration_seconds": duration_seconds,
        "duration_display": format_duration(info),
        "upload_date": iso_date(upload_date_raw),
        "upload_date_display": format_date(upload_date_raw),
    }


# ---------------------------------------------------------------------------
# Status/outcome (pure — decides exit code + stderr notes + JSON status)
# ---------------------------------------------------------------------------

def evaluate_results(*, video_count, skipped, timed_out, cutoff, period_label,
                      proc_returncode, stderr_text):
    """Decide status/exit-code/stderr notes from the collected results.

    Mirrors the original inline branching 1:1 so behavior (including the 120s
    partial-results safeguard) is unchanged; pulled out so it's testable
    without invoking yt-dlp. Returns a dict with status/exit_code/notes/error.
    """
    notes = []
    if video_count == 0 and skipped == 0:
        if proc_returncode not in (0, None) and stderr_text.strip() and not timed_out:
            notes.append(f"Error: yt-dlp failed:\n{stderr_text.strip()}")
            return {"status": "error", "exit_code": 1, "notes": notes, "error": stderr_text.strip()}
        if timed_out:
            notes.append(
                f"No results extracted within {TIMEOUT_SECONDS}s — this query is too "
                "slow to extract (try a narrower query or a longer window)."
            )
        else:
            notes.append("No results found.")
        return {"status": "empty", "exit_code": 0, "notes": notes, "error": None}

    if cutoff and skipped > 0:
        notes.append(f"(Filtered out {skipped} video(s) older than {period_label})\n")

    if video_count == 0:
        notes.append(f"No results found within the last {period_label}.")
        return {"status": "empty", "exit_code": 0, "notes": notes, "error": None}

    if timed_out:
        notes.append(
            f"(Note: hit the {TIMEOUT_SECONDS}s extraction budget — showing "
            f"{video_count} partial result(s); more may exist.)\n"
        )
        return {"status": "partial", "exit_code": 0, "notes": notes, "error": None}

    return {"status": "ok", "exit_code": 0, "notes": notes, "error": None}


# ---------------------------------------------------------------------------
# Payload assembly (pure — the JSON contract)
# ---------------------------------------------------------------------------

def build_payload(*, query, requested_count, months, days, cutoff, period_label,
                   videos_raw, skipped, timed_out, status, error):
    """Assemble the stable JSON contract: query/window metadata, status, videos."""
    videos = [normalize_video(v) for v in videos_raw]
    return {
        "query": query,
        "requested_count": requested_count,
        "window": {
            "months": months,
            "days": days,
            "no_date_filter": cutoff is None,
            "cutoff_date": iso_date(cutoff) if cutoff else None,
            "period_label": period_label,
        },
        "status": status,
        "timed_out": timed_out,
        "timeout_seconds": TIMEOUT_SECONDS,
        "skipped_older_than_window": skipped,
        "result_count": len(videos),
        "videos": videos,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Rendering (pure)
# ---------------------------------------------------------------------------

def render_table(videos):
    """Human-formatted results table (the default stdout output)."""
    divider = "─" * 60
    lines = []
    for i, v in enumerate(videos, 1):
        lines.append(divider)
        lines.append(f" {i:>2}. {v['title']}")
        meta = (
            f"{v['channel']} ({v['subscribers_display']} subs)  ·  "
            f"{v['views_display']} views  ·  {v['duration_display']}  ·  "
            f"{v['upload_date_display']}"
        )
        lines.append(f"     {meta}")
        if v["views_per_subscriber_display"] != "N/A":
            lines.append(f"     Engagement: {v['views_per_subscriber_display']} views/subs")
        lines.append(f"     {v['url'] or 'N/A'}")
    lines.append(divider)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main():
    # Force UTF-8 output on Windows to handle emoji in video titles. Done here
    # (not at import time) so importing this module for tests doesn't
    # reconfigure the real sys.stdout/stderr.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    query, count, months, days, json_mode = parse_args(sys.argv)

    try:
        ytdlp = resolve_ytdlp()
    except RuntimeError as exc:
        if json_mode:
            payload = build_payload(
                query=query, requested_count=count, months=months, days=days,
                cutoff=None, period_label=describe_period(months, days),
                videos_raw=[], skipped=0, timed_out=False,
                status="error", error=str(exc),
            )
            print(json.dumps(payload, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        sys.exit(1)

    fetch_count = compute_fetch_count(count, months, days)
    search_query = f"ytsearch{fetch_count}:{query}"
    cmd = build_search_cmd(ytdlp, search_query)

    cutoff = get_cutoff_date(months, days)
    period_label = describe_period(months, days)
    date_label = f", last {period_label}" if period_label else ""
    print(f"Searching YouTube for: \"{query}\" (top {count} results{date_label})...\n", file=sys.stderr)

    deadline = time.monotonic() + TIMEOUT_SECONDS
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace")
    try:
        videos_raw, skipped, timed_out = collect_results(proc.stdout, cutoff, count, deadline)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    stderr_text = (proc.stderr.read() or "") if proc.stderr else ""

    outcome = evaluate_results(
        video_count=len(videos_raw), skipped=skipped, timed_out=timed_out,
        cutoff=cutoff, period_label=period_label,
        proc_returncode=proc.returncode, stderr_text=stderr_text,
    )

    for note in outcome["notes"]:
        print(note, file=sys.stderr)

    payload = build_payload(
        query=query, requested_count=count, months=months, days=days,
        cutoff=cutoff, period_label=period_label, videos_raw=videos_raw,
        skipped=skipped, timed_out=timed_out,
        status=outcome["status"], error=outcome["error"],
    )

    if json_mode:
        print(json.dumps(payload, indent=2))
    elif payload["videos"]:
        print(render_table(payload["videos"]))

    sys.exit(outcome["exit_code"])


if __name__ == "__main__":
    main()
