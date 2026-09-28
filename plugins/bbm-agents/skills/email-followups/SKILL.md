---
name: email-followups
description: Write warm sales follow-up emails for a service business, from the first call to signed or closed-lost, in the owner's voice and from real notes. Covers the same-day call recap, no-shows, a proposal that went quiet, a lead who went cold, the close-the-loop (breakup) email, answering a reply (yes, question, objection, not now, no, wrong person, out of office, unsubscribe) and one-off follow-ups. Use when the owner says "follow up with", "they didn't show", "proposal went quiet", "write a recap of the call", "how do I reply to this", "they ghosted me", "what do I send them now", or pastes a prospect's email and asks what to say. Drafts only; nothing is sent.
---

# email-followups

Most service businesses lose deals in the gap after the call, not on it. The recap goes out Monday instead of today, the proposal gets one "any thoughts?" and then silence, and the no-show never gets rebooked. This skill writes the emails that close that gap: short, specific to what the person actually said, one clear next step each, and a clean stop.

It shares its format, rules and checker with `email-sequences`. The checker is `scripts/emailkit.py` in the **email-sequences** skill's folder, which from this skill's folder is `../email-sequences/scripts/emailkit.py`. Run it with `python3` on macOS/Linux, `python` or `py` on Windows.

## Pick the kind

| Situation | Kind | Cadence (days from the trigger) | Touches |
|---|---|---|---|
| Just had a sales or discovery call | `call-recap` | Day 0 (same day), Day 5 if the next step hasn't moved | 1-2 |
| They missed a booked call | `no-show` | Day 0, Day 2 or 3, Day 7 | 3 |
| Proposal or quote sent, no answer | `proposal` | Day 2, Day 5, Day 10, Day 17 | 4 |
| Warm lead went cold before a call or mid-conversation | `gone-quiet` | Day 0, Day 4, Day 10, Day 18 | 3-4 |
| Time to close it out | `breakup` | when the last touch is due | 1 |
| They replied and the owner needs an answer | `reply` | same day, within hours | 1 |
| Anything else the owner describes | `one-off` | when it makes sense | 1 |

The touches, the job of each and one example per kind are in `references/playbooks.md`. How to answer each type of reply is in `references/replies.md`. Read the matching section before drafting.

## Rules for every follow-up

1. **Any reply stops the sequence.** Including an out-of-office (pause until they are back). A follow-up that lands after someone already answered is the clearest sign of a machine. Their reply gets a `reply` draft instead.
2. **At least 2 days between touches** and **at most 5 touches, breakup included.** The checker enforces both inside a file. If an earlier file already went to this person, count those touches too.
3. **Every touch brings something new** and stands on its own: an answer to a likely question, a useful tip, a real result, a clear decision question, or a clean close. Never "just checking in", never a bare bump.
4. **Threading.** The first follow-up may go as a reply in the existing thread. Later touches start a new thread with a new subject that says what that email is about. For a reply in a thread, write `Subject: (reply in the <which> thread)` and let the owner's mail app add `Re:`; never type `Re:` or `Fwd:` yourself.
5. **No guilt, no fake urgency.** No "I guess you're busy", no "last chance" unless a real date is ending (a real price change, a real start date, a real season). Assume good faith: people are busy, not rude.
6. **If you send a breakup, honor it.** The sales follow-up stops for good. They go on a marketing list only if they already opted in or say yes to it. A later personal note is fine only for a genuinely new reason and only when the owner decides.
7. **Plain text, personal-looking.** One link at most per email, usually the booking link or the document they need.
8. **Offer two specific times plus the booking link as a fallback** whenever the ask is a call. Times in their time zone.

## Before you write

1. Run `emailkit.py paths [--business <name>]`. It prints the drafts folder and whether the brand files exist.
2. **Brand files.** Read `voice-agent.md`, `offers.md` and `email-voice.md` from the brand folder, and `brand-bible.md` for approved facts and proof. No `brand-bible.md` → stop and tell the owner to run `brand-bible` first. No `email-voice.md` → run `emailkit.py voice init` and build it with the owner by following `../email-sequences/references/voice.md`. Never write in a guessed voice.
3. **The facts of this deal.** Gather, from the owner or files they point you to:
   - Who: name, role, company, how they came in (referral, website, event), anyone else who decides.
   - What happened last, with dates: the call, the missed slot, the proposal sent, their last message.
   - **Their words.** Call notes, a transcript, or their emails. A recap is built on these; never write what someone said unless it is in the notes.
   - What was promised by whom, the next step, the booking link, and for proposals the scope and price as sent.
4. **Access.** Only read the owner's mailbox, calendar, call recorder or CRM if they say yes in this conversation, and only their own. Otherwise ask them to paste what you need.
5. Anything missing that the email needs: ask once, in one short list. If they can't answer, write `[Client to provide: what is needed]` or restructure so the email doesn't need it.

## Flow

1. **Gather** the facts above.
2. **Pick the kind** from the table. When unsure, ask the owner one question ("Did you already send a follow-up after the proposal?").
3. **Draft** in the shared format (`../email-sequences/references/draft-format.md`): frontmatter with `kind`, `business`, `audience`, `trigger`, `goal`, `exit` (for more than one email; any reply stops a follow-up), `format: plain`, `status: draft`; then one `## Email N: <its job>` block per touch with `Send:`, `Subject:`, `Preview:`, `CTA:` and the body as it would be sent.
4. **Notes for the owner** go between the `# Title` line and `## Email 1`: which notes you used, anything still open, and a reminder suggestion if one is due. The checker ignores that part.
5. **Final pass** from `../email-sequences/references/writing-rules.md`: every fact traces to a source, read it as the recipient on a phone, AI-tell sweep, cut 20 percent.
6. **Check:** `emailkit.py check <file>` must print `PASS`. Fix every error. Read every warning; fix it or tell the owner why it stays (a number that is a real result, for example).
7. **Report** to the owner (below).

## Where drafts go

The drafts folder printed by `emailkit.py paths`. One file per sequence; a single email is a sequence of one. Name: `YYYY-MM-DD-<kind>-<slug>.md`, where the date is today and the slug is the person or company in a few lowercase words (`2026-10-02-proposal-harbor-dental.md`). Never overwrite an existing draft; add `-v2`.

## Timing and sending

- **B2B service buyers:** Tuesday to Thursday, 8 to 10 am in the recipient's time zone. Trades and field businesses: early morning before jobs, or after 5 pm. Avoid Monday morning, Friday afternoon and weekends.
- **Exceptions that beat the window:** the call recap goes the same day, within a few hours. A no-show reschedule goes within an hour or two of the missed slot. A reply to their reply goes as soon as the owner can, within the same business day.
- **Day N** counts calendar days from the trigger. If a touch lands on a weekend or a public holiday, move it to the next weekday morning and keep the 2-day gap after it.
- Put the suggested day and time in each `Send:` line. The owner sends or schedules; you don't.

## Report to the owner

- Email 1 in full, ready to copy.
- The rest as a short list: touch number, send day, subject, and the angle it takes.
- What stops the sequence and what to do when they reply (bring the reply back here).
- Anything still `[Client to provide]`, and any reminder you suggest adding to their task list or CRM (with the date). You don't create it without their yes.
- The path to the draft file, and "from email-followups".

Expect edits. When the owner changes the wording, note the pattern (not the one-off) in `email-voice.md` under Learned preferences, with the date.

## Hard limits

- **Drafts only.** Never send, schedule, or queue an email, and never load one into an email platform or CRM, without the owner's explicit yes for that specific batch. Approval of email 1 is not approval of the sequence.
- **Never add anyone to a list or sequence** (marketing list, CRM sequence, newsletter) without an explicit yes for that batch, and never to a marketing list without their opt-in.
- **Never read the owner's mailbox, calendar or CRM** without their yes in this conversation.
- **Never invent** what someone said, a result, a client, a number, a price, a date or a deadline. Only the brand files, the owner, and the notes they gave you count as sources.
- **Unsubscribe or "stop" is final.** Tell the owner the same day to remove them from every list and sequence, and draft nothing further to that person.
