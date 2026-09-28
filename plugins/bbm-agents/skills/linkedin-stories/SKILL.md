---
name: linkedin-stories
description: Interview the owner and build their LinkedIn story bank - the real numbers, stories, opinions, mistakes and past writing every LinkedIn post draws on, so drafts stop inventing things and stop asking the same questions. A full interview the first time, a quick top-up later, or a focused interview that turns one topic into the raw material for a post. Use when the owner says "interview me", "build my story bank", "I don't know what to post about", "I've never posted", "add this story", or when linkedin-post or linkedin-plan finds no story bank.
---

# linkedin-stories

The story bank is `linkedin-stories.md` in the owner's brand folder. Every LinkedIn skill reads it; this is the only skill that writes it. It holds only what the owner said or confirmed.

Method adapted from the interviewer and voice builder in sergebulaev/linkedin-skills (MIT) and charlie947/social-media-skills (MIT).

Helper: `scripts/linkedin.py` in the **linkedin-post** skill (`python3` on macOS/Linux, `python` or `py` on Windows).

## Setup

`linkedin.py paths [--business <name>]`. No story bank → `linkedin.py stories init`. Read what's already there so you never ask for something it has.

## How to interview

- **One question at a time**, conversationally. Follow up on anything with a number, a date or a name in it; that's the gold.
- Push gently for specifics: "Roughly how much?", "When was that?", "What did the customer actually say?". Accept "I don't know" and move on.
- Never lead ("Would you say it was transformative?"). Never fill gaps with guesses.
- Stop when the owner wants to; save what you have. 15-20 minutes is a good first session.

## Full interview (first time)

Work through these areas, skipping anything the brand bible already answers:
1. **Receipts:** results, costs, time saved, before/after, counts ("how many clients / years / claims / jobs"). Each with what it refers to and when.
2. **Stories:** the customer they'll never forget; the job that went wrong; the moment they decided to start the business; the question customers always ask.
3. **Positions:** what their industry gets wrong; advice they disagree with; what they'd change if they ran the industry.
4. **Scars:** mistakes, lost deals, bad hires, what they'd do differently. Stated flat, with a date.
5. **Their words:** ask them to paste 3-5 things they wrote themselves (old LinkedIn posts, emails to customers, a talk transcript). This is the voice reference; save it whole.
6. **Off limits:** clients, people, numbers and topics never to mention. Ask about permission for any named person or company they mention.

## Quick top-up

"Anything happen lately worth a post?" plus 2-3 follow-ups. Add to the right section.

## Focused interview (one post)

For a single topic: what happened, when, the number, what the customer said, what they learned, what they'd tell someone in the same spot. Save it as a new story; hand it to `linkedin-post`.

## Writing it down

- Add to the right section of `linkedin-stories.md` under a short heading per item, in the owner's words where possible, with the date it was told: `### The Hale job rework (told 2026-09-28)`.
- Mark anything not cleared for naming: `(don't name the client)`.
- Edit entries in place when the owner corrects them; never keep two versions.
- After each session, show the owner a short list of what was saved and ask if anything is wrong or off limits.

## Report to the owner

A top-level message: how many receipts, stories and positions are in the bank now, the 2-3 strongest post ideas it suggests, the path to the file, and "from linkedin-stories". Offer `linkedin-plan` or `linkedin-post` next.

## Limits

Only the owner's own words and facts. Never invent, embellish or "improve" a story. Never save passwords, account numbers, health or financial details about identifiable people. Commit the file only if the workspace rules allow it.
