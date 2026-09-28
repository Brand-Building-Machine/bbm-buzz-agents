# Email draft format

Every email skill (`email-sequences`, `email-followups`, `email-onboarding`, `email-cold-outbound`) writes drafts in this one format, so `emailkit.py check` can lint them and the owner always sees the same shape.

One file per sequence (a one-off follow-up is a sequence of one). File name: `YYYY-MM-DD-<kind>-<slug>.md` under the email drafts folder (`emailkit.py paths` prints it).

```text
---
kind: welcome
business: Acme Plumbing
audience: Homeowners who downloaded the water-heater checklist
trigger: Downloads the water-heater checklist
goal: Book a free inspection call
exit: Books a call, replies, or unsubscribes
format: plain
status: draft
---
# Water-heater checklist welcome

## Email 1: Deliver the checklist
Send: Day 0, immediately
Subject: Your water-heater checklist
Alt subject: The checklist you asked for
Preview: Plus the one thing on it most people skip
CTA: Download the checklist

Body text here. Plain paragraphs. Links as [text](url).

Sam

## Email 2: The one check that matters most
Send: Day 2
...
```

## Frontmatter

| Field | Required | Notes |
|---|---|---|
| `kind` | yes | See the kinds table below. |
| `business` | yes | Which business, when the owner runs more than one. |
| `audience` | yes | Who gets this, in one line. |
| `trigger` | yes | What starts it (a download, a booked call, a signed contract, a no-show). |
| `goal` | yes | The one action the sequence exists for. |
| `exit` | yes when there is more than one email | What stops it early. Any reply stops a follow-up or cold sequence. |
| `format` | no | `plain` (default, looks like a personal email) or `designed` (newsletter-style template). |
| `emoji` | no | `allowed` only if the owner's voice uses emoji. Otherwise the checker rejects them. |
| `status` | yes | Always `draft`. The owner changes it; skills never do. |

## Kinds

| Kind | Skill | Words per email (target, hard limit) |
|---|---|---|
| `lead-magnet`, `welcome`, `nurture`, `sales`, `course`, `reengagement` | email-sequences | 50-350, 500 |
| `call-recap` | email-followups | up to 250, 350 |
| `no-show`, `proposal`, `gone-quiet`, `breakup`, `reply`, `one-off` | email-followups | up to 150, 220 |
| `onboarding` | email-onboarding | up to 300, 450 |
| `cold` | email-cold-outbound | 50-90, 125 |

## Each email

- Heading: `## Email N: <its one job>`, numbered from 1 in order.
- `Send:` when it goes. Use `Day N` counted from the trigger (`Day 0, immediately`, `Day 3, morning`). For event-based onboarding emails write `Send: on <event>` (`Send: on contract signed`).
- `Subject:` required. `Alt subject:` optional, one alternative to test.
- `Preview:` the preview text (the grey line after the subject in the inbox). Recommended.
- `CTA:` the one thing the reader should do. Required. `none` is allowed for a pure value email or a breakup email.
- Then a blank line and the body, exactly as it would be sent, signed off.
- Missing facts: `[Client to provide: what is needed]`. Never a made-up placeholder that reads as real.
- Personal details the email tool fills in (merge fields): write them as `[first name]`, `[company]`. The owner swaps them for their platform's tags (`{{ first_name }}`, `*|FNAME|*`) when loading. Never write platform tags in curly braces in a draft; the checker reads `{{...}}` as an unfilled slot.

## What the checker enforces

Errors (exit 1): missing frontmatter fields or email fields, em or en dashes (anywhere, including frontmatter and title), unfilled `{{SLOTS}}`, banned filler phrases, emoji without `emoji: allowed`, `Re:`/`Fwd:` subjects (for a same-thread follow-up write `Subject: same thread as Email 1`), body over the hard word limit, follow-up or cold touches under 2 days apart, more than 5 touches in a follow-up or cold sequence, any link or web address in the first cold email.

Warnings (exit 0, but read them): body over target length (word counts include the sign-off and any footer, not `[Client to provide]` text), a `Send:` line that isn't `Day N` or `on <event>`, a cold email with no opt-out line, subject over 60 characters, `!` or ALL CAPS in a subject, more than two links, a number, percentage or money amount that looks like a claim (confirm it is real), `[Client to provide]` still open.
