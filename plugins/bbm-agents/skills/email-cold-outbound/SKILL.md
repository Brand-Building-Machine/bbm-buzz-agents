---
name: email-cold-outbound
description: Write cold outreach emails to prospects who have never heard from the owner. Builds a short targeting brief, finds a true hook for each prospect from what the owner provides or public pages they point to, offers first-line options, then writes a 3-4 email sequence (plain text, no link in the first email) and reply templates, all as drafts checked by emailkit.py. Use when the owner says "cold email", "outreach to prospects", "prospecting emails", "reach out to these companies", "write an outbound sequence", or "nobody replies to my outreach". Drafts only; never sends, never scrapes or buys lists.
---

# email-cold-outbound

Cold email for a service business owner writing under their own name, usually from their own mailbox, to a small list of companies they chose. The job is not volume. It is a short, honest note that could only have been sent to that person, with an ask they can answer in five words.

## Which email skill

| Situation | Skill |
|---|---|
| They have never heard of the owner, did not ask for anything | **email-cold-outbound** (this one) |
| They met, called, asked for a quote, got a proposal, or went quiet | `email-followups` |
| They opted in (download, sign-up, customer list) | `email-sequences` |
| They signed | `email-onboarding` |

If someone on the list already knows the owner, it is not cold: use `email-followups` for them.

## Before you start

1. Run `emailkit.py paths [--business <name>]`. The script lives in the **email-sequences** skill: `../email-sequences/scripts/emailkit.py` relative to this skill's folder. Use `python3` on macOS/Linux, `python` or `py` on Windows. It prints the drafts folder and which brand files exist.
2. Read, from the brand folder: `brand-bible.md` (who they serve, proof), `offers.md` (what they sell), `voice-agent.md`, and `email-voice.md` (how the owner writes email, sign-off, postal address). Missing brand files: stop and offer `brand-bible`. Missing `email-voice.md`: follow `../email-sequences/references/voice.md` first. Never write in a guessed voice.
3. Read `../email-sequences/references/writing-rules.md` and `../email-sequences/references/draft-format.md`, then this skill's `references/copy.md`. Keep `references/replies-and-deliverability.md` for steps 6 and 7.
4. Get from the owner, if the brand files do not already say it:
   - **Ideal client:** the kind of business, the role that decides, size, area.
   - **Proof:** real results for similar clients, in their words. None yet: `[Client to provide]`, never an invented one.
   - **The prospects:** names, companies, emails, and anything they know about each (how they found them, mutual contacts, a public page to read). This skill writes; it does not find people.
   - **Where recipients are** (US, Canada, UK/EU, elsewhere). This changes what is allowed. See the compliance section in `references/replies-and-deliverability.md`.

## Flow

**1. Targeting brief.** Show the owner a short brief and get a nod before writing anything:

```
Who: <role> at <kind of business>, <size>, <area>
Why now: <the moment that makes them need it: hiring, growth, a new rule, a season>
The offer, in one line: <what they get>
Framed as: save time / make money / save money / reduce risk (pick one lead, one backup)
Proof we can use: <real result, source> or [Client to provide]
Low-friction ask: <e.g. "Worth a look?">
Recipients: <countries>. Compliance notes: <anything that blocks or changes the plan>
```

**2. Hooks per prospect.** For each prospect, find the strongest true hook, in this order: a buying signal (hiring, opening, expanding, a new rule that hits them) > a shared connection or client > something specific the owner genuinely knows about their business > a comparable result for a similar client. Use only what the owner gave you or public pages the owner pointed to; read those pages if you can, and quote where the fact came from. **No real hook: say so, and write a short, honest cold email labeled `cold` in the table.** Never fake familiarity ("loved your recent post") or invent a signal.

**3. First-line options.** For the first prospect (or the batch's shared angle), offer 2-3 first lines using different strategies from `references/copy.md`, with a one-line recommendation. The owner picks. Then write the rest of the table in the chosen style.

**4. Sequence.** Write 3-4 emails in the draft format, default Day 0 / 3 / 7 / 11 (at least two days apart, five touches is the hard cap). Email 1 new thread, no link, no attachment, no image. Email 2 in the same thread. Email 3 a new thread with a new subject and a new angle. Email 4 a clean close, often asking for the right person. Each email stands alone and brings something new. Structures, CTA ladder, subjects and a full example are in `references/copy.md`. Include the owner's postal address and an easy way to say no (see compliance).

**5. Final pass.** Run the writing-rules final pass, then the three-pass cut and the 0-100 score from `references/copy.md`. Anything under 85 gets another pass. Any invented fact, fake familiarity or fake `Re:` fails outright.

**6. Check.** `emailkit.py check <draft file>` must PASS (exit 0). Read every warning; fix it or tell the owner why it stays.

**7. Report** to the owner: the brief in two lines, how many prospects and how many have a real hook versus plainly cold, the recommended first line, the path to both files, any open `[Client to provide]`, and the deliverability and compliance notes that apply to them. Offer the reply templates from `references/replies-and-deliverability.md`.

## Output

Two files in the drafts folder that `emailkit.py paths` prints:

- `YYYY-MM-DD-cold-<slug>.md`: the sequence, in draft format, `kind: cold`, `exit:` "Any reply, bounce or opt-out". Email 1 is written out in full for the first prospect in the table.
- `YYYY-MM-DD-cold-<slug>-prospects.md`: one row per prospect. The first line (and subject, if it changes) is the only part that differs per person; everything else must read true for everyone in the batch.

```
| Prospect | Company | Hook type | The fact | Source | First line |
|---|---|---|---|---|---|
| <name, role> | <company> | buying signal | Hiring a billing coordinator | Their careers page, <url>, read <date> | <line> |
| <name, role> | <company> | cold | None found | n/a | <honest cold line> |
```

Every fact has a source: a URL the owner pointed to (with the date it was read) or "owner said, <date>". No source, no fact.

## Hard limits

- **Drafts only.** Never send, schedule, or load anything into a mail client, CRM or sending tool. Each batch the owner sends needs their explicit yes for that batch.
- **Never scrape, buy or build lists**, and never guess email addresses. The owner brings the prospects.
- **Never invent** a hook, a result, a client, a number or a mutual contact. Missing proof is `[Client to provide]`.
- **Business contacts only.** Never write to consumers at personal addresses. Canadian recipients generally need consent first; UK/EU need a legitimate-interest basis (see compliance).
- **Honor every opt-out** across every sequence the owner runs, the same day. Any reply stops the sequence for that person.
- This skill gives general information on email law, not legal advice.
