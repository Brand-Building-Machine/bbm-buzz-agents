---
name: email-sequences
description: Write the owner's email sequences that turn a new lead into a buyer, in the owner's own voice. Covers lead magnet delivery, welcome and nurture, the sales sequence, a 5-day email course, and re-engaging a quiet list. Also sets up the owner's email voice file, which the other email skills share. Use when the owner says "write a welcome sequence", "emails for my lead magnet", "nurture sequence", "sales emails", "email course", "what should I email my list", "re-engage my list", or "set up my email voice". For follow-ups after calls, proposals and no-shows use email-followups; after someone buys, email-onboarding; for prospects who never opted in, email-cold-outbound.
---

# email-sequences

This skill writes the emails that carry someone from "downloaded the free thing" to "booked a call" or "bought". It is built for **service businesses**: consultants, agencies, brokers, bookkeepers, coaches, trades. The goal of most sequences is a conversation (a reply or a booked call), not a checkout.

The script is `scripts/emailkit.py`, relative to this skill's folder (the folder containing this SKILL.md). Run it with `python3` on macOS/Linux, `python` or `py` on Windows. The sibling email skills use the same script.

## The path a lead walks

```
lead magnet  ->  welcome / nurture  ->  sales  ->  (booked call: email-followups)  ->  (bought: email-onboarding)
    2 emails        5 to 7 emails       5 or 6
```

| Kind | When | Emails | Pace |
|---|---|---|---|
| `lead-magnet` | Right after someone downloads or signs up for a freebie | 2 | Day 0, Day 1 or 2 |
| `welcome` | New subscriber (with or without a lead magnet) | 5 to 7 | Every 2 to 3 days, Days 2 to 16 |
| `nurture` | Longer relationship-building for a list that is not ready to buy | 6 to 8 | Every 3 to 7 days |
| `sales` | Presenting a specific offer to people who know you | 5 or 6 | Every 1 to 2 days |
| `course` | A 5-day email course used as the lead magnet itself | 6 (Day 0 to Day 5) | Daily |
| `reengagement` | Subscribers who haven't clicked or replied in about 90 days | 3 | Days 0, 4, 10 |

Full playbook for each, with the job of every email: `references/sequences.md`. Worked examples: `references/examples.md`.

## Before you write

**1. Find the files.** `emailkit.py paths [--business <name>]` prints the drafts folder and which brand files exist. Read `brand-bible.md`, `offers.md`, `voice-agent.md` and `email-voice.md`.
- No brand folder: stop and offer the `brand-bible` skill. Never write in a made-up voice or invent the offer.
- No `email-voice.md`: build it first. Run `emailkit.py voice init`, then follow `references/voice.md` (the owner's real sent emails are the source). If the owner wants to skip it, write from `voice-agent.md` and say the emails will sound closer to them once the voice file exists.

**2. Gather what this sequence needs.** Ask only for what the files don't already answer, two or three questions at a time, each with your suggested answer so the owner corrects instead of composing.

| Sequence | Must know |
|---|---|
| `lead-magnet` | What the freebie is and where it lives (link), one quick win from inside it, who signs |
| `welcome`, `nurture` | Who the reader is, their main problem, the belief that keeps them stuck, the offer this leads to, the owner's "why I do this" story, one real client story (or none, and you work around it) |
| `sales` | The offer (name, what's included, price or range if public, how to buy or book), the top two objections, the strongest real proof, any real deadline or limit |
| `course` | Topic, what the reader can do after Day 5, the format (see sequences.md), any offer on Day 5 |
| `reengagement` | What the list was promised, what's changed or new, whether the owner will actually remove non-responders |

**3. Map the belief shift** in one line before drafting: from what they believe now to what they need to believe to buy ("I just need a cheaper bookkeeper" to "clean books every month is what gets me a loan"). Every nurture and sales email moves the reader one step along it.

## Write

1. Read `references/writing-rules.md` and `references/draft-format.md`. They are the standard for every email.
2. Write the whole sequence as one file in the drafts folder: `YYYY-MM-DD-<kind>-<slug>.md`, in draft format (frontmatter, then `## Email N: <job>` blocks with Send, Subject, Alt subject, Preview, CTA, body).
3. One job per email. Hook first. Plain text unless the owner's sending profile says designed.
4. Real facts only. Missing proof means `[Client to provide: ...]` or an email built so it doesn't need it (a belief shift instead of a case study).
5. Every sequence has an `exit`: booked a call, replied, bought, or unsubscribed. People who book leave for `email-followups`; people who buy leave for `email-onboarding`.

## Check

1. Do the final pass in `writing-rules.md` (fact check, read as the recipient, AI-tell sweep, cut 20 percent).
2. `emailkit.py check <file>` must print `PASS`. Fix every error. Read every warning: each number flagged as a claim must trace to a real source, and every `[Client to provide]` goes in your report.

## Report to the owner

Keep it short and in this order:

- Which sequence, who it's for, and the one goal it drives.
- **Email 1 in full.** Then the rest as a list: day, subject, and the one job of each email.
- What's still `[Client to provide]` and who should supply it.
- Where the file is.
- How to use it: paste into their email tool as an automation, or send by hand. Offer to adapt it for their platform if they name it.

Then ask what to change. When they edit, save the pattern in `email-voice.md` under Learned preferences with the date.

## Limits

- **Drafts only.** Never send, schedule, import contacts, or load a sequence into an email platform without the owner's explicit yes for that specific action. If a connector could do it, still ask first and say exactly what will happen.
- Never read the owner's mailbox or CRM without their yes, and only their own.
- Never invent a testimonial, result, statistic, client name, deadline or price. A fake deadline is still a fake.
- Marketing emails need an unsubscribe link and the business postal address. The owner's email platform usually adds both; remind them if they send by hand.
- Commit only files this skill wrote, and only if the workspace map allows agents to commit.
