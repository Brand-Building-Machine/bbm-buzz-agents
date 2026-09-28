---
name: email-onboarding
description: Draft the emails a service business sends after a client says yes - welcome, what we need from you, kickoff agenda and recap, how we work together, first win, 30-day check-in, and a review or referral ask timed to a real win - plus friendly reminders when the client hasn't sent what's needed. Built around how the owner's onboarding actually runs, in their voice, as drafts for approval. Use when the owner says "onboard a new client", "welcome email for a new client", "we just signed X", "kickoff email", "ask for a review", "client onboarding sequence", or "the client hasn't sent their documents". Drafts only; nothing is sent.
---

# email-onboarding

The sale is made. These emails are not selling; they **reinforce the decision**, get the client what they need to start, and make the first weeks feel organised. A new client who hears nothing for three days after paying starts to wonder. A client who gets a clear "here's what happens next" relaxes and does their part.

The helper is the shared email checker in the **email-sequences** skill: `../email-sequences/scripts/emailkit.py`, relative to this skill's folder (the folder containing this SKILL.md). Run it with `python3` on macOS/Linux, `python` or `py` on Windows. Read these once per session before drafting:

- `../email-sequences/references/draft-format.md` (the file shape; kind is always `onboarding`)
- `../email-sequences/references/writing-rules.md` (the quality bar and the final pass)
- `references/sequence.md` (the default sequence, timing, branch table, full examples)
- `references/access-and-intake.md` (asking for access and documents safely, intake lists by service type)

## 1. Inputs

1. `emailkit.py paths [--business <name>]` prints the drafts folder and which brand files exist. If the owner runs more than one business, ask which one first.
2. **Brand files.** Read `voice-agent.md`, `offers.md` (what the client bought: what's included, the steps, the timeline) and `email-voice.md`. `brand-bible.md` for anything else.
   - No `brand-bible.md` or `voice-agent.md`: stop and offer to run the `brand-bible` skill. Don't write in an invented voice.
   - No `email-voice.md`: run `emailkit.py voice init`, then build it with the owner following `../email-sequences/references/voice.md`. Existing client emails are the best evidence here, because onboarding emails are one-to-one.
3. **The owner's existing material.** Search the workspace for a welcome email, intake form, onboarding checklist, kickoff agenda or contract they already use. Reuse their real steps and wording; don't redesign a process that works.
4. **For a specific new client** ("we just signed X"): the client's name, what they bought, the signing date, and any notes from the sales call. Use only what the owner or their files give you. Nothing about the client is guessed.

## 2. The owner interview

Onboarding is different in every business, so ask before you draft. Rounds of 2-3 questions, each with your recommended answer (from their files, or the default in `references/sequence.md`) so the owner corrects instead of composing. Skip anything their files already answer and say where you got it.

- **Round 1, the first 48 hours.** What happens right after signing (contract, invoice, payment, a portal invite)? Does your software already send anything automatically, so we don't duplicate it? Who is the client's main point of contact, and how do they reach that person (email, direct line)?
- **Round 2, what you need from them.** Intake form, documents, logins or access, decisions? How do clients share those today? By when do you need them before work stalls? (Recommend the safe methods in `references/access-and-intake.md`.)
- **Round 3, kickoff and first delivery.** Is there a kickoff call? How long, who attends, how it's booked? What is the first deliverable and roughly when does it land? What should the client have in hand after 30 days?
- **Round 4, how you work.** Communication rhythm and channel, normal reply time, reporting cadence, how a client raises a problem, office hours or days off.
- **Round 5, the relationship.** When do you check in? Where do you want reviews (one link, usually the Google Business Profile)? Do you ask for referrals or testimonials, and is there anything your profession restricts? (Some licensed fields, such as insurance, financial advice, legal and healthcare, have rules on testimonials. Ask the owner to confirm theirs.)

Then ask the one question that decides the shape: **which events can you actually see?** (Contract signed, kickoff booked, intake received, first deliverable sent.) Event-based emails only work if someone or something notices the event. If the owner sends by hand, write the trigger as plain instructions they can follow.

## 3. Flow

1. **Interview** (above).
2. **Map the steps.** Adapt the default in `references/sequence.md` to their answers: drop emails that don't apply (no kickoff call means no emails 3 and 4), merge where the owner's process is short, and fill in their real steps and timings. Show the map as a short table (number, job, `Send:`, CTA) plus the branch table, and get a nod before writing. This is where they correct you cheaply.
3. **Draft** in the draft-format: `kind: onboarding`, one file for the main sequence, a second small file for the reminders when there's something to chase. Time-based sends are `Send: Day N` counted from signing; event-based sends are `Send: on <event>` (`Send: on kickoff booked`). Every email: one job, one CTA, plain text, signed by the person the client will actually deal with.
4. **Final pass** from `writing-rules.md`: fact check, read as the client on a phone, AI-tell sweep, cut 20 percent. Then the onboarding checks:
   - The next step and its timing are clear in the first three lines.
   - Nothing asks for a password, a full card or bank number, or an ID number by email (see Hard limits).
   - Goals and decisions in the kickoff recap are the client's words from the call notes, never invented.
   - The review ask sits behind a delivered win and a happy check-in, never on a fixed day alone.
5. **Check:** `emailkit.py check <file>` must print `PASS` for every file. Read each warning; fix it or tell the owner why it stays (a `[Client to provide]` the owner must fill is fine to leave, and gets listed in the report).
6. **Report** (below).

## 4. Where drafts go

The drafts folder from `emailkit.py paths`. File names: `YYYY-MM-DD-onboarding-<slug>.md` for the sequence and `YYYY-MM-DD-onboarding-<slug>-reminders.md` for the nudges. The slug is the service for a reusable template (`monthly-bookkeeping`) or the client for a one-client version. `status: draft` always; only the owner changes it.

## 5. Presenting to the owner

A short message, not the whole file:

- The sequence as a table: each email's job, when it sends, its one ask.
- The branch rules in one line each (from the branch table).
- Every open `[Client to provide]` and who should fill it (usually a link, a phone number or a real step).
- What they need to set up to send it: the events someone has to watch, and whether each email goes by hand or from their tool.
- The paths to the files, and "from email-onboarding".

Then ask which emails to change. When the owner edits a draft, record the pattern (not the one-off) under **Learned preferences** in `email-voice.md` with the date.

## Relationship emails, not marketing

These go to someone who is paying the owner. Write them like the owner writing to one client:

- **Plain text, from a person,** with their normal signature. No banner, no newsletter layout, no "Dear valued client".
- **No promotion.** No upsells, no "you might also like", no newsletter content inside an onboarding email. In the US, CAN-SPAM treats an email whose main purpose is an existing transaction or relationship differently from a commercial one; mixing in promotion can make it a marketing email that needs an opt-out and a postal address. Rules differ elsewhere. Keep them purely about the client's work.
- **Specific over polished.** Dates, names of the people involved, the exact thing needed. A client should be able to act on each email without scrolling back through the thread.
- **Reply-friendly.** Every email invites a reply to a real person. Never a no-reply address.

## Hard limits

- **Drafts only.** Never send, schedule, load into an email platform or CRM, or add anyone to a list without the owner's explicit yes for that specific batch.
- **Never ask a client for a password in email,** and never write one into a draft. Access goes through the tool's own invite or delegate access, or a password manager share (`references/access-and-intake.md`). The same goes for full card or bank account numbers and ID numbers: those go through a secure portal or a phone call.
- **Never invent** client names, goals, results, dates, prices, testimonials or review counts. Missing: ask, or `[Client to provide: what is needed]`.
- **Never ask for a review or referral** after a complaint, a missed deadline, a billing or payment issue, or a negative check-in. Stop the ask and tell the owner (see the branch table). Never offer anything in exchange for a review; platforms such as Google prohibit it.
- **No em dashes or en dashes** anywhere in client-facing text.
