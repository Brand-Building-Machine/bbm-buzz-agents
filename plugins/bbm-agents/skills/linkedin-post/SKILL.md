---
name: linkedin-post
description: Write LinkedIn text posts in the owner's voice from their real stories and numbers. Picks one proven post formula by what the post should earn (comments, reposts, likes, saves), drafts two versions, runs an edit pass that strips AI tells, and checks the copy. Can also review or fix a draft the owner wrote, or rewrite something from another platform for LinkedIn. Use when the owner says "write a LinkedIn post", "post about X", "turn this into a LinkedIn post", "fix my post", "does this sound like AI", or linkedin-plan hands over a slot. Drafts only; nothing is posted.
---

# linkedin-post

A good LinkedIn post is one real thing the owner knows, said the way they'd say it, with a first line that stops the scroll. The formula gives it a shape; the owner's specifics make it land. Method adapted from sergebulaev/linkedin-skills (MIT) and charlie947/social-media-skills (MIT).

The helper is `scripts/linkedin.py` in this skill's folder (`python3` on macOS/Linux, `python` or `py` on Windows).

## Before you write

1. `linkedin.py paths [--business <name>]` prints the drafts folder, the brand files, the LinkedIn profile and the story bank.
2. **Brand files are required.** Read `voice-agent.md` (how they sound), `brand-bible.md` (customer, proof, compliance) and `offers.md` (only if the post points at an offer). Missing → stop and offer `brand-bible`. Never write in an invented voice.
3. Read `linkedin.json` (the profile: author, personal or company page, audience, pillars, goal). Missing → ask the three things that matter (who the posts are for, 2-4 topics they post about, personal or company page), then `linkedin.py profile init` and fill it in with them.
4. Read `linkedin-stories.md` (the story bank) if it exists. Its "Their words" section is the best voice reference there is: match its sentence length, vocabulary and habits over the brand voice doc when they differ, because a personal LinkedIn post is the owner talking, not the company. No story bank → suggest `linkedin-stories` once; carry on if they'd rather not.
5. **Compliance.** If `brand-bible.md` lists compliance rules (insurance, finance, health, legal), they override everything here. No guarantees, no promised outcomes, no client details without permission.

## Step 1: Pin the post down

From the request, the plan slot, or one short question, get:
- **Topic and the one point** the post makes, in a sentence.
- **The real material:** a number, a story, a date, a customer situation. Look in the story bank first. If there's none, ask **one** specific question ("What did that cost, and when?"). Don't draft around a hole.
- **Goal:** comments, reposts, likes or saves. Default from `linkedin.json` or pick by material.

## Step 2: Choose the formula

Open `references/hooks.md`. Pick **one** formula by goal and material. Say which and why in one line.

## Step 3: Draft two versions

Two versions with **different first lines** (and different formulas if two fit). For each:
- **Line 1:** the hook. A number or fact, not a question. Under about 140 characters, making sense alone.
- **Body:** one idea, one or two sentences per paragraph, blank lines between. Personal-page posts in first person ("I", "we"); company pages in the brand voice.
- **Length:** most good posts land between 900 and 1,600 characters. Short is fine when the idea is short; never pad.
- **Close:** a specific question drawn from the post, a clean last line, or a P.S. with a real follow-up.
- **First comment:** any link goes here, not in the post.
- **Visual:** say whether it wants none, a single image (`linkedin-image`) or a carousel (`linkedin-carousel`), and why in one line. Don't make the visual here.

Every fact traces to the story bank, the brand files or the owner. Missing → `[Client to provide]`, never a guess.

## Step 4: Edit pass and check

Follow `references/edit-pass.md` on both versions. Then `linkedin.py lint <draft file>` must report **no errors**; fix or consciously keep each warning.

## Output

`linkedin.py new post --slug "<topic>" [--business <name>]` makes the dated folder. Save `post.md`:

```
# LinkedIn post: <topic> (<date>)
Page: <personal / company> | Goal: <comments/reposts/likes/saves> | Pillar: <pillar> | Formula: <name>
Source: <story bank entry / what the owner said>

## Post A
<text exactly as it would be pasted>

## Post B
<text>

## First comment
<link or extra detail, or "none">

## Visual
<none / single image / carousel, and why>

## Notes
<what's [Client to provide], anything to check with the owner>
```

Keep the `## Post A` / `## Post B` headings exactly; `linkedin.py lint` reads them.

No em dashes in anything you write for the owner, including README and plan files (use a comma, colon or full stop).

## Fixing a draft the owner wrote

Skip Steps 1-3. Run the edit pass and the checker on their text, change only what the pass calls for, and show a short list of what changed and why. Keep their voice; don't rewrite for style.

## Rewriting from another platform

Newsletter, blog, video transcript, a thread: find the one idea that works alone on LinkedIn, pick a formula, write a new first line for the fold, and move any link to the first comment. Never paste the original with light edits.

## Report to the owner

A top-level message: the topic and formula, **Post A's first line and Post B's first line** (so they can pick without opening the file), anything `[Client to provide]`, the path to `post.md`, and "from linkedin-post". Offer the visual as the next step if one was suggested.

## Limits

Drafts only. Never post, schedule, comment or message on LinkedIn, and never ask for their LinkedIn password. Never invent stories, numbers, clients, quotes or results. Never name a client, employee or partner without the owner confirming it's okay.
