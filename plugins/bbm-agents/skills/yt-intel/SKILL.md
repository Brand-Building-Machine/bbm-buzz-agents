---
name: yt-intel
tier: routine
status: beta
category: Intelligence / Learning
description: >-
  BETA. Turn ONE YouTube link into a skimmable brief: what the video is
  about, how it compares with what the owner already runs (their own skills,
  notes and workspace), what is genuinely new to them vs already known, and
  suggested next steps. Also handles multi-link batches with a ranked triage
  list on top of the individual briefs, and long videos (2h+). Use when the
  owner drops a YouTube link and asks "what's this about", "is this worth
  watching", "what's in this video", "yt-intel this", or pastes a URL with no
  other context. Default is a fast pass; add "deep" / "--deep" for a thorough
  one. Optional add-on on explicit request only: an atomic granular-capture
  list ("atomic list", "granular capture") - see step 5. If the owner asks a
  specific question about a video, use yt-ask instead.
---

# yt-intel

The owner runs into videos constantly and can't watch them all. This turns one
link into a fast read: what it's about, whether the owner already has or knows
this, and what (if anything) to do about it. The differentiator is grounding:
every "this is new" or "you already do this" claim cites the actual skill,
note, or workspace fact it was checked against. A takeaway with no citation is
flagged as unverified, never stated as fact.

## How to run the scripts (read once)

This skill is installed from a plugin, so its files do **not** live in the
owner's workspace or the current working directory. Always run the script by
its path relative to **this skill's own directory**, the folder that contains
this `SKILL.md`:

```
python "<this skill's dir>/scripts/fetch.py" "<youtube-url>" [--deep] [--video] [--out-dir <folder>]
```

- `<this skill's dir>` is the absolute path of the directory this SKILL.md was
  loaded from. Substitute the real path; keep it in quotes (install paths can
  contain spaces).
- Interpreter: on Windows use `python` (or `py`). On macOS/Linux use `python3`
  if `python` is not found.
- The script finds everything it needs relative to its own file, so it works
  from any working directory.

## Prerequisites

- **`yt-dlp`**, as the `yt-dlp` command or the Python module
  (`python -m pip install -U yt-dlp`). Keep it updated; YouTube changes often
  break old versions.
- **Optional: the owner's own Gemini key** in the `GEMINI_API_KEY` environment
  variable (a `.env` file in the working directory is also read if present).
  No key is bundled with this skill. The key is only used for the rare
  fallback when a video has no captions. Without it, captioned videos (almost
  all of them) work exactly the same; uncaptioned ones report "transcript
  unavailable" with the reason. The fallback also needs `pip install google-genai`.

## Flow

### 1. Fetch

Run `fetch.py` as above. It extracts the video ID and pulls metadata via
`yt-dlp -j --no-download` (title, channel, upload date, duration, view count;
no video file touches disk). It writes `{video_id}.json` and prints a status
line including the path it wrote and which fetch method produced the
transcript.

Output location: `--out-dir` if given, else `$YT_SKILLS_DATA_DIR/yt-intel/` if
that variable is set, else the per-user cache folder
(`%LOCALAPPDATA%\yt-skills\yt-intel` on Windows, `~/Library/Caches/yt-skills/yt-intel`
on macOS, `~/.cache/yt-skills/yt-intel` on Linux). Read the JSON from the path
the script printed.

**Transcript sources, in priority order:**
1. **YouTube captions**, fetched directly via `yt-dlp`'s caption URLs: free,
   instant, no model call, no length ceiling, no key needed. This is the path
   for almost every video. Manual captions are preferred over auto-generated;
   the structured `json3` format is preferred over `vtt`. `fetch_method`
   reports `captions-manual` or `captions-auto`.
2. **Gemini video/audio understanding** (optional, owner's own key) - only
   when no caption track exists, or the caller passes `--video` (for the rare
   case where the caption transcript is judged to be missing load-bearing
   on-screen content). When captions fail or are skipped, the JSON's
   `caption_fallback_reason` says why.

**Three Gemini fetch methods, routed by video length** (fallback path only):
- `video-default` - Gemini reads the YouTube URL at full visual resolution.
  Keeps on-screen text and screen-share demos. Up to ~50 min.
- `video-low` - same, at low media resolution (cheaper, loses fine on-screen
  detail). ~50 min to ~2h45m.
- `audio` - `yt-dlp` extracts the audio track only and it is transcribed from
  audio alone. Past ~2h45m, or as a last resort when a shorter video still hits
  the token ceiling. Needs `ffmpeg` installed.

If Gemini comes back with the token-ceiling error regardless of the duration
guess, `fetch.py` steps down to the next cheaper method automatically. Every
Gemini attempt (method + model + real error) is recorded in the JSON's
`attempts` list (empty when captions succeeded). **Read `fetch_method` before
judging a thin brief on a long video**: `audio` had zero visual channel, so a
video that leans on on-screen code will read thinner. That is expected.

A transient Gemini failure gets one more real attempt before giving up.

If the script exits 2 ("transcript unavailable"), stop and tell the owner
plainly, quoting the real `last_error` from the output, not a generic "video
unavailable." Only conclude private/age-restricted/region-locked if that is
what the error says. Don't guess at the content from the title.

### 2. Ground against the owner's workspace

The comparison is against **the owner's** setup, never a generic one. Your
persona or instructions supply the owner's workspace root and routing (where
their skills, notes and docs live). Use that:

- Their skills: skill folders in the workspace (for example `.claude/skills/*/SKILL.md`,
  `.agents/skills/*/SKILL.md`, or wherever the routing says) - read names and
  descriptions.
- Their standing docs: the workspace's `CLAUDE.md` / `AGENTS.md` and any
  notes or knowledge folders the routing names.

**If no workspace routing was given, or nothing is readable there, skip the
"New to you" comparison entirely** and say so in the brief:
`New vs known: skipped - no owner workspace available to compare against.`
Never compare against your own general knowledge and present it as the
owner's setup.

### 3. Judge [agent step - the core of the skill]

Read the fetched JSON, then work through the sections below. **Mode controls
depth, not which sections exist.** Default is quick; go deep only if the owner
asked or the fetch ran with `--deep`.

**Quick (default)** - sized for a video the owner is half-curious about:
- Outline: 5-8 bullets, in the video's own order.
- New vs known: the 2-4 most load-bearing claims/techniques only.
- Comparison: search skill names/descriptions and the top-level workspace docs
  for keyword overlap with those claims. Don't crawl the whole workspace.
- Next steps: 0-3 lines, only if something actually warrants action.

**Deep** ("deep dive" / "go deep on this" / `--deep`):
- Outline: fuller, can exceed 8 bullets if the video earns it.
- New vs known: every claim worth judging.
- Comparison: also search the owner's notes/knowledge folders and any
  archived or work-in-progress skill folders (an idea might already be built
  and shelved, which is its own finding). Use web search if a claim's currency
  is genuinely in question.
- Next steps: fuller, can include who/what would own it if it is build-shaped.

For each claim you bucket:
- **ALREADY-DO** - name the exact skill or file in the owner's workspace.
- **NEW** - the owner doesn't have this and it is plausibly worth having. Say
  where it would slot in if you can see one; "no obvious slot-in yet" if not.
- **COULD NOT VERIFY** - you searched and found neither a match nor a clean
  absence (e.g. depends on an account/plan tier you can't check). Never
  silently drop these into NEW or ALREADY-DO to make the answer cleaner.

Never state "this is new to you" without having actually searched. If you
didn't check something, say so; silence reads as verified.

### 4. Content angle (optional, default is zero)

Only when the owner's workspace shows they publish their own content and they
want angles from videos. **Default output is zero.** A video earns a candidate
only by clearing all four gates, in order:

1. **Has a gap.** A real place the owner disagrees, adds context, or has seen
   the opposite play out. "This was a good video" is not a gap.
2. **Business-first.** Nameable as a business/leadership/operations story with
   the tool as supporting cast, not the headline.
3. **The owner has hands-on proof** - they actually ran it themselves or with
   their customers. No proof, no angle. Never invent their proof.
4. **Not a recycled trend** and not already in the owner's content notes.

Most videos fail at gate 1 or 3. **That is the correct, expected result.** A
version of this step that finds an idea in every video is broken. Never relax
a gate to produce output.

On a clearing candidate (max one):

```
## Content angle
**Source:** {video title} - {creator} - {url} - watched {date}
**The gap:** one sentence - what the video claims vs. what the owner has seen
**Draft take:** 1-2 sentences, business-first
**Proof needed from the owner:** the concrete example that would back this -
  UNCONFIRMED until the owner supplies it
```

When nothing clears: `No content angle. Reason: {named gate failed}.` Always
name the gate.

### 5. Atomic capture (optional add-on, not part of the default output)

Run only when explicitly asked for the "atomic list" / "granular capture" on a
specific video. The default outline is deliberately compressed; this is the
opposite: the raw granular inventory.

1. Reuse the `{video_id}.json` from step 1 if it still exists; otherwise
   re-run `fetch.py`.
2. Walk the full transcript in order. Pull out every separable, atomic
   concept: a setup step, a named routine or config choice, a specific
   technique, a concrete claim. **One idea per entry.** Only merge two entries
   if they are literally the same concept restated.
3. One line per entry: `{concept} - {teaching|take}`. A "take" is an opinion
   and needs the owner's own proof before it is used; everything else is
   teaching. No ranking, no prose padding.
4. File it separately from the main brief (same place, `-atomic` suffix) and
   add one line at the bottom of the main brief: `**Atomic capture:** see {filename}`.

### 6. Write + present

- **Print the full brief in chat.** This is the primary deliverable.
- **File it** only if the owner's workspace routing names a place for research
  notes: `{date}-{video-slug}.md` there, with frontmatter
  `type: reference`, `created: {date}`, `tags: [yt-intel, youtube]`. If there
  is no such place, don't invent one; say the brief was not filed.

## Report shape

```markdown
# {video title}
{channel} · {upload date} · {duration} · [{url}]({url})
{fetch method note - only when the method was not captions or video-default,
e.g. "Fetched via audio only (very long video) - no visual channel."}

## What it's about
- {outline bullet}

## New vs known
**Already doing this:**
- {claim} - see `{skill-or-file}` ({one line on how it compares})

**New to you:**
- {claim} - {why it's plausibly worth it; slot-in if there is one}

**Couldn't verify:**
- {claim} - {what would need checking}

(or: "New vs known: skipped - no owner workspace available to compare against.")

## Next steps
- {0-3 concrete lines, or "Nothing actionable - informational only."}

## Content angle
{candidate block, or "No content angle. Reason: {gate}." - omit the section
entirely if step 4 does not apply to this owner}
```

## Batch runs

When 3+ links arrive together (or the owner says "here's a batch"):

1. Fetch + judge each one individually, same as a single run.
2. Then add ONE ranked triage list on top: what actually matters, in order,
   with a one-line why each. Name cross-video overlap once instead of
   repeating it in every brief (two creators pitching the same tactic days
   apart is itself a signal). Expect most of a real batch to rank low; an
   inflated ranked list defeats the point.
3. Don't hold early videos waiting for stragglers; a late link gets its own
   brief and, if it changes the ranking, a short note.

## Output

The brief in chat (+ the filed copy when the workspace has a place for it).
Nothing is sent, posted or deployed; this skill only reads and reports.

## What this is NOT

- Not a question-answering tool for one video - that's `yt-ask`.
- Not bulk research across many videos - that's `yt-corpus`.
- Not YouTube search/discovery - that's `yt-search`.
- Not a transcription tool for local files.

## Known gaps

- Tested on real batches of mixed lengths (2 min to 2h24m), Shorts, and
  `youtu.be` / `m.youtube.com` / timestamp-param URLs. Untested: non-English
  audio, and videos past ~3 hours on the Gemini audio path.
- The Gemini fallback is occasionally flaky, not duration-correlated; the
  script retries once automatically and surfaces the real error in
  `last_error` / `attempts`.
- The "Couldn't verify" bucket depends on how thoroughly you search in quick
  mode. Deep mode narrows this but doesn't eliminate it.
- No memory across runs: every run starts cold, so a repeat link is only
  caught if a filed brief exists.

## Tests

```
python -m pytest "<this skill's dir>/tests" -q
```
