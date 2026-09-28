# Replies, deliverability and compliance

What to do when someone answers, how to keep cold email out of spam folders, and the email laws an owner should know about before sending. Replies are drafts too: the owner reads and sends each one.

## Replies

Any reply stops the sequence for that person, even an out-of-office (until they are back). Reply fast: within the same working day, ideally within the hour. Keep replies shorter than the email they answer, in the owner's voice.

| Reply | What it looks like | What to do |
|---|---|---|
| **Interested** | "Sure", "tell me more", "what does it cost?", shares availability | Answer in two or three lines. Offer two specific times, with the booking link as a backup. |
| **Question** | Asks how it works, price, who else you work with | Answer the question plainly and briefly, using only real facts. Then one ask. Never invent a price or a client to answer it. |
| **Objection** | "We already have someone", "too expensive", "we do it in-house" | Acknowledge it, offer one relevant fact or a small next step, and leave it there. No argument, no second push. |
| **Not now** | "Maybe next quarter", "busy season" | Thank them, ask if it's OK to check back at the time they named, and note the date. If they say no, that's a no. |
| **Wrong person** | "Not me", "talk to our office manager" | Thank them and ask who handles it. If they name someone, that person is a new cold prospect: start fresh, don't forward the old thread. |
| **Out of office** | Auto-reply with a return date | Don't reply. Pause and resume the day after they are back. |
| **Reschedule** | "Can we move it?" | Offer two new times straight away, plus the booking link. |
| **Unsubscribe** | "Remove me", "stop", "not interested, don't email again" | Remove them from every sequence and list the owner runs, the same day. One line back, then never again. |
| **Angry** | "How did you get my email?", "this is spam" | Apologise in one sentence, say where the address came from if asked (honestly), confirm removal. Remove them everywhere the same day. Don't defend the email. |
| **Bounce** | "Address not found", mailer-daemon | Stop. Mark the address bad. If more than a couple bounce in one batch, stop the batch and check where the addresses came from. |

Reply shapes (adapt to the owner's voice):

```
Interested:
Great, thanks for the quick reply. Does Tuesday at 10 or Wednesday at 2 work for 15 minutes?
If neither does, here's my calendar: <booking link>
<sign-off>

Wrong person:
Thanks for pointing me the right way. Who looks after <area> at <company>? I'll reach out to them directly.
<sign-off>

Not now:
Understood, thanks for saying so. Mind if I check back in <month they named>?
<sign-off>

Unsubscribe:
Done, you won't hear from me again. Sorry for the interruption.
<sign-off>

Angry:
Sorry about that. I found your address on <where, honestly> and I've removed it; you won't hear from me again.
<sign-off>
```

Once a week, look at the replies together: the same objection twice means the next batch's copy should answer it up front.

## Deliverability basics

Advice for the owner. This skill does not set up domains, mailboxes or sending tools.

- **Authenticate the domain.** The sending domain should have SPF, DKIM and DMARC set up. The email provider (Google Workspace, Microsoft 365, and most others) has a guide; whoever manages the domain can usually do it in an hour. Without these, mail to Gmail and Outlook is more likely to land in spam or be rejected.
- **Plain text, like a personal email.** No images, no designed template, no attachments. Turn off open and click tracking for cold email; tracking adds a hidden image and rewritten links that spam filters notice.
- **No link in email 1.** Ask for a reply instead. A link can come later, or after they reply.
- **Keep volume low and steady**, especially from the owner's main mailbox. Start with around 10-20 new cold emails a day, spread through the day, and grow slowly. A sudden jump from zero to hundreds looks like spam.
- **A brand-new mailbox or domain needs warming.** Use it for normal email for a few weeks before sending cold email from it.
- **Protect the main domain.** The owner's main domain carries client email and invoices. If cold email ever grows beyond a small, careful volume, consider a separate domain for it (a close variant of the business name, honestly branded), so a spam problem there does not hurt everyday email. It needs its own authentication and warm-up, which is why it is not worth it at small volume.
- **Only write to addresses you have good reason to believe are right**: from the prospect's own website, a card they gave, or the owner's contacts. Guessed addresses bounce, and bounces hurt the domain for months.
- **Watch the signs.** Replies saying "spam", several bounces, or a sudden drop in replies mean stop and check before sending more.

## Compliance

General information, not legal advice. Laws change and details depend on the business and the recipient; the owner should check their own situation, and ask a lawyer if they are unsure. When the recipient's country is unclear, ask before writing.

**Everywhere, always:**

- Business contacts only, at business addresses, about something relevant to their role. Never cold email consumers at personal addresses.
- Honest sender name, honest subject line, no fake `Re:` or `Fwd:`.
- Say who the owner is and how to reach them, including a postal address for the business.
- A clear, easy way to say no (a line like "Not relevant? Say so and I won't email again."), and honor it quickly and everywhere: every sequence, every list, for good.
- Keep a simple record of who opted out, so nobody gets emailed twice by mistake.

**United States (CAN-SPAM).** Cold business email is allowed without prior consent if it follows the rules: accurate "from" and header details, a subject that is not misleading, clear that it is a commercial message, a valid postal address, a clear way to opt out, and opt-outs honored within 10 business days (same day is the standard here). The owner is responsible even if someone else sends for them.

**Canada (CASL).** Commercial email generally needs consent first. The exceptions are narrow: for example, an existing business relationship, or an address the person published openly for their business role (with no "no unsolicited email" note) when the email is relevant to that role. Messages must identify the sender, include contact details and an unsubscribe that works. Default: don't cold email Canadian recipients unless one of the exceptions clearly applies; ask the owner.

**UK and EU (GDPR, and the UK's PECR).** A named person's work email is personal data. Writing to them usually relies on "legitimate interests", which means the owner should do and keep a short legitimate interest assessment (why it is relevant to them, why they would reasonably expect it, how easy it is to object). Tell them where their details came from and how to object, and stop at once if they do. In the UK, emailing company staff is allowed without prior consent under these conditions, but sole traders and some partnerships count as individuals and need consent. Some EU countries require consent even for business email; check the country. Consumers need consent.

**Elsewhere.** Many countries (Australia, for example) require consent for commercial email. If recipients are outside the US, Canada, UK and EU, tell the owner to check the local rules before sending.
