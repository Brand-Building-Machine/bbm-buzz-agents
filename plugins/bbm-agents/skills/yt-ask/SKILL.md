---
name: yt-ask
tier: tool
status: beta
category: Intelligence / Learning
description: >-
  BETA. Answer ONE specific question about ONE YouTube video. Pulls the transcript
  (captions first, Gemini video/audio fallback for videos without them) and
  answers what was actually asked, instead of writing a standard brief. Use
  when the owner pastes a link WITH a question attached — "what does he say about
  X", "does this cover Y", "what's their pricing", "did they explain how Z
  works", "at what point do they demo the thing". The narrow sibling of
  `yt-intel`: same transcript plumbing, different output. If the owner pastes a
  bare link with no question, that is `yt-intel`, not this. Requires the
  sibling `yt-intel` skill (same plugin).
---

# yt-ask

`yt-intel` answers "what's in this video and does the owner already know it," always in
the same shape. That is the right output when they are triaging. It is the wrong output
when they have one specific question and want one specific answer.

This skill is the second case. Same video, same transcript path, no brief.

## Which one to run

| The owner posts | Run |
|---|---|
| A bare link | `yt-intel` |
| A link + "is this worth watching" / "what's this about" | `yt-intel` |
| A link + an actual question | **`yt-ask`** |
| Several links | `yt-intel` batch |
| A topic, no link | `yt-search` |

## How to use

This skill is installed from a plugin, so its files are not in the owner's workspace or
the current working directory. Run the script by its path relative to **this skill's own
directory** (the folder containing this `SKILL.md`), substituting the real absolute path
and keeping it quoted:

```bash
python "<this skill's dir>/scripts/ask.py" "<url>" "<question>" [--deep] [--video] [--json] [--max-chars N]
```

On Windows use `python` (or `py`); on macOS/Linux use `python3` if `python` is not found.
The script locates the sibling `yt-intel` skill relative to its own file, so any working
directory is fine.

### Parameters
- `<url>` — any YouTube URL form (watch, youtu.be, shorts, embed)
- `<question>` — required, quoted. What the owner actually asked, in their words.
- `--deep` — thorough transcription pass (only matters on the Gemini fallback path)
- `--video` — skip captions, force the video/audio path. Use when captions exist but are
  visibly garbage, or when the answer depends on what is on screen rather than said.
- `--max-chars N` — truncate very long transcripts (default 400,000; `0` disables)
- `--json` — emit the structured payload instead of formatted text

### Examples

```bash
# The normal case
python "<this skill's dir>/scripts/ask.py" "https://youtu.be/abc123" "what does he say the pricing is?"

# Captions are garbage, the answer is on screen
python "<this skill's dir>/scripts/ask.py" "https://youtu.be/abc123" "what tools are in his sidebar?" --video

# A three-hour conference talk
python "<this skill's dir>/scripts/ask.py" "https://youtu.be/abc123" "does she mention MCP?" --max-chars 800000
```

## What it does and does not do

It **fetches**, it does not answer. Output is the video's metadata, the question, and the
transcript, formatted for you — the calling agent — to answer from directly.

That is deliberate. Having this script call a model to summarize, then answering from the
summary, would put two model hops between the owner and the source and lose the exact
wording their question usually turns on. One hop. You read the transcript yourself.

Transcript acquisition is imported wholesale from `yt-intel/scripts/fetch.py` — captions
first, Gemini video/audio fallback routed by duration. This skill owns none of it, so a fix
there is a fix here. (Both skills ship a package named `scripts`, so `ask.py` loads
`fetch.py` by explicit file path, relative to its own location; a plain import silently
resolves to the wrong package.)

## Answering rules

These are not optional. The whole value of this skill is that its answers are grounded.

- Answer **only** from the transcript. Quote it where a quote settles the matter.
- If the transcript does not answer the question, **say exactly that.** Do not fill the gap
  from what you know about the topic, the channel, or the title. A confident wrong answer
  about a video the owner has not watched is the worst possible output here.
- If the transcript was truncated, the output says so and names the character count. Do not
  claim the video "never mentions" something when you only read the head and tail — say the
  middle was not read, and offer to re-run with a larger `--max-chars`.
- If there is no transcript at all, the output gives you metadata only. Say the transcript
  could not be retrieved. Do not answer from the title.

## Exit codes

`0` when a transcript was obtained. `1` for a fetch error or no transcript — the text output
explains which, and the calling agent should surface that rather than proceeding.

## Prerequisite

Same as `yt-intel`: the `yt_dlp` Python module (`python -m pip install -U yt-dlp`); the
CLI binary is optional, `fetch.py` falls back to `python -m yt_dlp` when it is absent.

**No API key is needed for captioned videos** (almost all of them). Only videos with no
captions (or `--video`) use the optional Gemini fallback, which needs the owner's **own**
key in the `GEMINI_API_KEY` environment variable plus `pip install google-genai`. No key
ships with this skill; without one, those videos report "no transcript" with the reason.

## Tests

```bash
python -m pytest "<this skill's dir>/tests" -q
```

22 tests: truncation accounting and budget, the three payload statuses (ok / error /
no_transcript), flag pass-through, and the render-layer guarantees (that a fetch failure
tells the caller not to answer, and that a missing transcript warns against guessing).
