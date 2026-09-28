---
name: yt-corpus
tier: tool
status: beta
category: Intelligence / Research
description: >-
  BETA. Build a BULK YouTube transcript corpus for a research question: flat-search
  many candidates, pull 20-30 full timestamped transcripts in parallel, and run
  a cheap per-video extraction pass against the question. Saves every full
  transcript permanently so a content team can mine it later. Use when the need
  is "what is the whole field saying about X" and a 2-3 video sample would not
  answer it. The bulk-read counterpart to `yt-intel` (ONE link, deep grounded
  brief against the owner's workspace). Invoked by `youtube-scout` inside a
  research run, or by the owner directly. Requires the sibling `yt-intel`
  skill (same plugin).
---

# yt-corpus

Read 30 videos instead of 3, in less wall-clock than reading 3 used to take.

## Why this exists

The research team's YouTube path was `yt-search` (discovery) → `yt-intel` (one
grounded brief per video). `yt-intel` is expensive per video, so `youtube-scout`
was told to cut to a handful. That instruction predates yt-intel's **2026-08-18
captions-first redesign**, which made raw transcripts effectively free. The
ration outlived its reason.

Two costs were being conflated:

| | Cost | Verdict |
|---|---|---|
| **Reading** a video | ~4s, free, no length ceiling (captions) | should never have been rationed |
| **Briefing** a video | a full grounded pass against the owner's workspace | correctly rationed — still `yt-intel`'s job |

**Discovery was the real bottleneck all along.** `yt-search` runs
`ytsearch{count*3}: --dump-json`, extracting full metadata one video at a time
(~15-20s each, 120s budget, usually returns partial). Measured on a real run:

| | Old path | yt-corpus |
|---|---|---|
| Discover 30 candidates | ~16 min (observed, still partial) | **1.9s** |
| 12 videos → transcripts | not attempted at this size | **~20-100s** |
| Full run, 7 transcripts + extracts | — | **~85-130s** |

The difference is subscriber counts, which `yt-search` needs for its
views-to-subs outlier ratio. That is a **content-selection** metric, not a
research one, so we drop it. `upload_date` is also absent from flat mode — but
the caption step already needs a full `yt-dlp -j` per video (that is where
caption URLs live), and that call carries the date. So date filtering moves
*after* the parallel stage and costs nothing. Net: one `-j` per video,
parallelized, doing double duty — versus a serial `-j` for discovery plus a
second `-j` for the transcript.

## Usage

This skill is installed from a plugin, so its files are not in the owner's workspace or
the current working directory. Run the script by its path relative to **this skill's own
directory** (the folder containing this `SKILL.md`), substituting the real absolute path
and keeping it quoted. On Windows use `python` (or `py`) and put the whole command on one
line (the `\` line continuations below are for macOS/Linux shells); on macOS/Linux use
`python3` if `python` is not found. Any working directory is fine: the script finds the
sibling `yt-intel` skill relative to its own file.

```bash
python "<this skill's dir>/scripts/sweep.py" "<research question>" \
  -q "<search query>" [-q "<another query>"] \
  [--per-query 20] [--max-videos 30] [--months 12] [--no-date-filter] \
  [--min-seconds 180] [--max-per-channel 3] [--concurrency 4] \
  [--run-dir <research run folder>] [--slug <name>] [--no-extract]
```

The **question** drives the extraction pass; the `-q` **queries** drive
discovery. They are different things — write 2-4 queries that a practitioner
would actually type, ordered by weight (earlier queries win ties on dedup).

`stdout` is the corpus path and nothing else, so a calling agent can capture it.
All progress goes to stderr.

**Where the corpus goes:** `<run-dir>/evidence/youtube/` when `--run-dir` is given
(use an absolute path to the research run folder you were told to write to). Without
`--run-dir` it lands in the per-user data folder, `<data dir>/yt-corpus/<slug>/`, where
`<data dir>` is `$YT_SKILLS_DATA_DIR` if set, else `%LOCALAPPDATA%\yt-skills` (Windows),
`~/Library/Caches/yt-skills` (macOS) or `~/.cache/yt-skills` (Linux). That location is
scratch; anything worth keeping should be written with `--run-dir`.

### Examples

```bash
# Inside a research run — corpus lands in the run folder's evidence/
python "<this skill's dir>/scripts/sweep.py" \
  "What are practitioners actually running for multi-agent orchestration?" \
  -q "LangGraph multi agent production" -q "CrewAI vs LangGraph" \
  --run-dir "<absolute path to the research run folder>"

# Transcripts only, no model calls at all
python "<this skill's dir>/scripts/sweep.py" "Meta Advantage+ 2026" \
  -q "Advantage plus shopping campaigns 2026" --no-extract
```

## What it writes

```
<corpus>/
  INDEX.md            ← read this first; self-sufficient
  manifest.json       ← every video, status, path, word count, why it dropped
  transcripts/{id}.md ← FULL timestamped transcript + provenance front-matter
  extracts/{id}.json  ← per-video structured extract against the question
```

**Full transcripts are permanent and are the point.** The extract is a lens over
the transcript for *this* question, never a replacement. A later run — or the
content team — will want material this run had no reason to pull, and re-fetching
is not guaranteed (videos get deleted, captions get disabled). `INDEX.md` is
written to be self-sufficient because **`trend-analyst` has no fetch tools by
design** (Read/Glob/Grep only) and must be able to spot patterns across all 30
videos without opening anything else.

Timestamps are load-bearing, not decoration: **`fact-checker` must independently
verify a claim at source**, and its contract forbids accepting a scout's artifact
as evidence. A timestamp lets it jump to the exact moment in the real video.

## The evidence label — the most valuable field

Every claim is labelled, and the levels are judged **only by what the words
prove**, because captions cannot see the screen:

- **`demonstrated`** — narrating a live run and reacting to real output: *"okay,
  it returned three results"*, *"that took about four seconds"*, *"huh, that
  failed"*. Reacting to a real result is the tell.
- **`narrated`** — walkthrough language with no observed result: *"so we add the
  tool here"*. They are probably showing something; the transcript does not prove
  it worked.
- **`asserted`** — a general claim with no run behind it.

"Let me show you" is **not** a demo. An intention to demo is not a demo.

A first version of the prompt collapsed everything to `asserted` (23 of 23 on a
live video) — it read the caption text as pure speech and never credited a
narrated result. The three-way split fixed it: the same batch now returns
**36 demonstrated / 43 narrated / 59 asserted**.

**Known limit, do not paper over it:** a video whose value is *visual* (a UI
walkthrough, a dashboard demo) will under-report `demonstrated`, because the
audio never says what the screen showed (captions only carry speech). When a
video's whole substance is on screen, send that ONE video through
`yt-intel --video` — that is exactly what yt-intel is still for (needs the
owner's own Gemini key).

## Cutting rules (applied before any network spend)

- **Shorts dropped** (`--min-seconds`, default 180). A 45s clip is not evidence
  of practice.
- **Per-channel cap** (`--max-per-channel`, default 3). `trend-analyst` counts
  one source repeated as ONE source, so ten videos from one creator actively
  wastes the run rather than strengthening it.
- **Date window** applied post-fetch. **Undated videos are kept and flagged**,
  never silently dropped.

## Failure handling

Every failure is recorded in `manifest.json` and surfaced in `INDEX.md` under
**Gaps — not in this corpus**, with its error text. A silently missing video is
indistinguishable from a video that had nothing to say, which is why nothing is
swallowed.

YouTube rate-limits the caption endpoint harder than the metadata call. Observed
429s at 8-wide, and again at 5-wide with a shallow backoff (2 of 12 videos lost).
Current defaults — 4-wide, 0.35s global spacing, 4 retries with jittered backoff
capped at 20s — recovered 11 of 12 on re-run. If you see repeated 429s, lower
`--concurrency` rather than retrying the same command.

## Relationship to the other YouTube skills

| Need | Skill |
|---|---|
| What is the whole field saying about X (20-30 videos) | **`yt-corpus`** |
| One link, deep, graded against the owner's workspace | `yt-intel` |
| One specific question about one video | `yt-ask` |
| One visual/UI-demo video where captions miss the substance | `yt-intel --video` |
| Ranked candidates with views-to-subs outlier ratios (content picking) | `yt-search` |

`yt-corpus` **does not replace `yt-intel`** — it replaces yt-intel's *misuse* as
the research team's bulk reader.

## Requirements

- `yt-dlp`, as the command or the Python module (`python -m pip install -U yt-dlp`).
- **Optional:** the owner's **own** Gemini key in the `GEMINI_API_KEY` environment
  variable (plus `pip install google-genai`) for the per-video extraction pass. No
  key ships with this skill. Without it the script still writes every full
  transcript and `INDEX.md`, and says it skipped extraction; the calling agent can
  read the transcripts itself.
- The sibling `yt-intel` skill: the caption path is loaded from
  `yt-intel/scripts/fetch.py` (by file path, relative to this skill) rather than
  duplicated. **One caption implementation, three consumers** (yt-intel, yt-ask,
  yt-corpus) — fix a caption bug once.

## Tests

```bash
python -m pytest "<this skill's dir>/tests" -q   # 21 tests, no network, no key
```
