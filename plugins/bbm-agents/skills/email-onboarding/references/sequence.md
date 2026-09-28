# The default onboarding sequence

A starting shape for a service business, adapted to the owner's answers from the interview. Most owners end up with five to eight emails. Drop what doesn't apply, merge what's short, and never add an email that has no job.

Timing: `Send: Day N` counts from the day the client signed. `Send: on <event>` fires when something happens (the kickoff is booked, the first deliverable goes out). Event-based beats time-based whenever the owner can see the event: a recap sent the day of the call is useful, one sent "Day 5" might arrive before the call.

## The emails

| # | Job | Default send | The one ask |
|---|---|---|---|
| 1 | Welcome: you made a good call, here's what happens next | on contract signed, same day | Reply (a phone number, a quick hello) |
| 2 | What we need from you, and book the kickoff | Day 1 | Book the kickoff (intake first) |
| 3 | Kickoff confirmation and agenda | on kickoff booked | Reply if something on the list is hard to find |
| 4 | Kickoff recap | on kickoff call ended, same day | Reply with anything we got wrong |
| 5 | How we work together | on day after kickoff recap, or Day 7 | Reply if the rhythm doesn't suit them |
| 6 | First win and progress update | on first deliverable sent | The one thing still needed from them |
| 7 | 30-day check-in | Day 30 | Reply with one thing to change, or "all good" |
| 8 | Review, referral or testimonial ask | on happy check-in reply, after a delivered win | One review link, or reply with two sentences |

Email 5 sits early on purpose: expectations are cheapest to set before the first "why haven't I heard from you?". If the owner's kickoff already covers it, fold the key lines into the recap and drop email 5.

### 1. Welcome

Job: reduce buyer's remorse and remove the "now what?" gap. Include: a thank-you in the owner's voice, one line on why this was a good decision (tied to what the client said they wanted, not a boast), the next steps as a **numbered list with when each happens**, and exactly who to contact and how. Keep it short. Don't ask for documents yet; that's email 2's job, and a welcome that opens with homework feels like a bill.

### 2. What we need from you, and book the kickoff

Job: get everything needed to start, in one place, and a kickoff on the calendar. Include: a numbered list of each item with how to share it safely (see `access-and-intake.md`), how long it takes, the date it's needed by, and why it matters in one line. Say plainly that you never need their passwords. Put the booking link last, after the prep, so they book once they've seen what's involved.

### 3. Kickoff confirmation and agenda

Job: make the call productive and show the client the owner runs a tight process. Include: date, time and time zone, how to join, who attends, a three-point agenda, what to bring, and what they'll leave with. Mention any missing intake items here, kindly.

### 4. Kickoff recap

Job: one written record both sides can point to. Include: **their goals in their words** (quoted from the call notes), decisions made, who does what by when, and open questions. Never invent a goal or a decision; if the notes are thin, ask the owner or mark `[Client to provide]`. Send it the same day while the call is fresh.

### 5. How we work together

Job: set expectations so small silences don't become worries. Include: how and when updates arrive, the normal reply time, the reporting cadence, who to contact for what, and **how to raise a problem** (and that the owner wants to hear it early). Only real commitments the owner will keep.

### 6. First win and progress update

Job: show value early and keep the client's part moving. Include: what's done (specific), what's next and when, and the one thing still needed from them. The first win is whatever the client can see: a finished deliverable, a fixed problem, a clear report. It is not "we're making great progress".

### 7. 30-day check-in

Job: catch problems while they're small and learn how the client feels. Ask **one real question** with an easy reply ("What's one thing we should do differently?" or "On a scale of 1 to 10, how's it going so far?"). Tell them a problem goes straight to the owner, and that the owner will call. No review ask in this email.

### 8. Review, referral or testimonial ask

Job: turn a happy client into proof, only once they are happy. Send only when **all** are true: a win has been delivered, the check-in reply was positive, and there is no open complaint, missed deadline or billing issue. Include: a thank-you that names the specific win, one line on why it helps (other business owners decide by reading reviews), and **one** easy action: a single review link, or "reply with two sentences about what changed, and whether I can share it with your first name". Ask for one thing only: a review, a referral or a testimonial, whichever the owner values most right now. Never offer anything in exchange for a review.

## Branch table

The owner (or their tool) watches for these. Each row says what to do instead of the next scheduled email.

| If | Then |
|---|---|
| Intake, documents or access not received by Day 3 (or 2 business days before the kickoff) | Send reminder 1: friendly, lists only what's still missing |
| Still missing three days after reminder 1 | Send reminder 2: offer to do it together on a short call |
| Still missing after reminder 2 | Stop emailing. The owner calls the client. Two nudges is the limit |
| Kickoff not booked by Day 3 | Fold the booking link into reminder 1; don't send a separate nudge |
| Client replies with a question at any point | A person answers it. The next email waits until the question is resolved |
| Client raises a complaint or seems unhappy at any point | Pause the sequence and alert the owner the same day. Skip email 8 |
| Billing or payment issue (failed payment, disputed invoice) | Pause emails 7 and 8 until it's resolved and the client is happy again |
| Check-in reply is negative, lukewarm or a low score | No review ask. Alert the owner to call within one business day |
| Check-in reply is positive and a win has been delivered | Send email 8 |
| No reply to the check-in | No review ask. The owner decides whether to call |
| Client already left a review or sent a referral | Skip email 8; send a short personal thank-you instead |

## Example: the main sequence

A fictional bookkeeping firm, "Northwind Bookkeeping", with owner Sam. The facts in it (a 45-minute kickoff, books closed by the 10th, QuickBooks) are what this fictional owner said in the interview; a real draft uses only the real owner's facts. Links use `example.com`; a real draft uses the owner's links from `email-voice.md`, or `[Client to provide: booking link]`.

```markdown
---
kind: onboarding
business: Northwind Bookkeeping
audience: A small business owner who just signed for monthly bookkeeping
trigger: Signs the monthly bookkeeping agreement
goal: Books handed over cleanly and a first month closed, with a happy client
exit: Client raises a complaint, a billing issue comes up, or the client asks to pause
format: plain
status: draft
---
# Monthly bookkeeping onboarding

## Email 1: Welcome and what happens next
Send: on contract signed, same day
Subject: Welcome to Northwind, here's what happens next
Alt subject: You're all set. Here's the plan
Preview: Three steps, and who to call if anything's unclear
CTA: Reply with the best number to reach you

Hi Jordan,

Thanks for signing today. Getting the books off your plate before tax season was a good call, and I'm glad you picked us.

Here's what happens next:

1. Tomorrow I'll send a short list of what we need from you, with a link to book your kickoff call.
2. On the kickoff (45 minutes) we walk through your accounts and agree what "done" looks like each month.
3. About two weeks after the kickoff, you get your first month of clean books.

I'm your main contact for everything. Reply here or call me on (555) 010-0142.

One small thing for now: reply with the best number to reach you, in case we need a quick answer during setup.

Sam

## Email 2: What we need from you, and book the kickoff
Send: Day 1
Subject: What we need before your kickoff
Preview: About 20 minutes of setup, and none of it is passwords
CTA: Book your kickoff call

Hi Jordan,

Here's everything we need to get started. It takes about 20 minutes, and we'd like it by Friday so the kickoff can be about your numbers, not logistics.

1. The intake form (10 minutes). It asks about your business, your accounts and who else we should talk to. It ends with a secure upload for your last three months of bank and card statements: [start the intake form](https://example.com/northwind/intake).
2. Access to QuickBooks. Inside QuickBooks, open Manage users, choose the Accountants tab and invite sam@northwind.example. You stay the owner and can remove us any time.

We never need your passwords, so please don't send them by email. The invite and the secure upload keep your details safe.

Once that's done, pick a time for the kickoff: [book your kickoff call](https://example.com/northwind/kickoff).

Sam

## Email 3: Kickoff agenda and what to bring
Send: on kickoff booked
Subject: Your kickoff call: agenda and what to bring
Preview: 45 minutes, and you'll leave with a clear monthly plan
CTA: Reply if anything on the list is hard to find

Hi Jordan,

You're booked. The video link is in your calendar invite, and it's just you and me.

What we'll cover:

1. How money comes in and goes out of the business today.
2. Anything messy we should know about (old accounts, personal spending on the business card, late invoices).
3. What you want from your books each month, and when.

Please have your QuickBooks login handy (for you, not for us) and a rough idea of your biggest questions about your numbers.

You'll leave with a monthly close date, a list of who does what, and answers to anything that's been bugging you.

If anything on the intake list is hard to find, reply and tell me. We can work around most of it.

Sam

## Email 4: Kickoff recap
Send: on kickoff call ended, same day
Subject: Notes from today's kickoff
Preview: Your goals, what we agreed, and who does what
CTA: Reply with anything I got wrong

Hi Jordan,

Thanks for the time today. Here's what we agreed, so we're both working from the same page.

What you told me you want: "I want to open my laptop on the 10th and know whether we made money last month."

What we decided:

1. We close your books by the 10th of each month.
2. Receipts go in the shared folder as you get them, not in a pile at month end.
3. The old savings account stays out of the books until your accountant confirms it's personal.

Who does what:

1. Sam: finish cleaning up last month by the 24th.
2. Jordan: send the two missing card statements by Wednesday.
3. Sam: ask your accountant about the savings account this week.

If I got anything wrong or missed something, reply and tell me. This is the version we'll both work from.

Sam

## Email 5: How we work together
Send: on day after kickoff recap
Subject: How we'll keep you in the loop
Preview: When you'll hear from us, and how to reach me fast
CTA: Reply if any of this doesn't suit how you work

Hi Jordan,

A quick note on how working together goes from here, so you always know when to expect us.

1. Your books are closed by the 10th, and you get a one-page summary by email the same day.
2. I reply to emails within one business day. If it's urgent, call me on (555) 010-0142.
3. Questions about a transaction come to you in one batch each month, never one email at a time.
4. If something isn't right, tell me straight away. I'd much rather fix a small thing this week than hear about it at year end.

If any of that doesn't suit how you work, reply and we'll change it.

Sam

## Email 6: First month closed
Send: on first month closed
Subject: Your first month is done
Preview: What we finished, what's next, and one thing we need
CTA: Reply with notes on the four transactions

Hi Jordan,

Your books for last month are closed and reconciled. Your one-page summary is attached, and the short version is on the first line.

What's done:

1. Every bank and card account matches the statements.
2. Last month's income and expenses are categorised.
3. The old savings account is set aside, as your accountant confirmed.

What's next: we close this month by the 10th, same as agreed.

One thing we need from you: four transactions we couldn't identify are listed at the bottom of the summary. A word or two on each is plenty.

Sam

## Email 7: One-month check-in
Send: Day 30
Subject: One month in, how are we doing?
Preview: One question, and it's a real one
CTA: Reply with one thing to change, or "all good"

Hi Jordan,

It's been a month since you signed, so I want to ask properly: what's one thing we should do differently?

It can be small. The format of the summary, how often we email, anything that's been slightly annoying.

If something's actually wrong, reply and I'll call you the same day to sort it out.

And if it's all good, a two-word reply is perfect.

Sam

## Email 8: A small favour
Send: on happy check-in reply, after first month closed
Subject: A small favour
Preview: Two minutes, and it helps other business owners decide
CTA: Leave a short Google review

Hi Jordan,

Thanks for the kind reply. Hearing that you finally know where the business stands each month made my week.

Most business owners pick a bookkeeper by reading reviews, so a few honest lines from you would help the next one find us.

If you're happy to, here's the link: [leave a short review](https://example.com/northwind/review). Two sentences is plenty.

No worries at all if not.

Sam
```

## Example: the reminders

Two nudges, three days apart, each naming only what's still missing and making it easier than the last. After reminder 2, the owner picks up the phone; a third email is where a new client relationship starts to feel like debt collection.

```markdown
---
kind: onboarding
business: Northwind Bookkeeping
audience: A new bookkeeping client who hasn't sent everything needed to start
trigger: Intake, statements or QuickBooks access not received by Day 3
goal: Everything needed to start is received before the kickoff
exit: Everything is received, the client replies, or reminder 2 goes unanswered and Sam calls
format: plain
status: draft
---
# Onboarding reminders: missing intake items

## Email 1: Reminder one, what's still missing
Send: on intake items still missing at Day 3
Subject: Two things left before your kickoff
Preview: The intake form is done, thank you. Just these two
CTA: Send the QuickBooks invite

Hi Jordan,

Thanks for filling in the intake form. Two things are still missing before we can get started:

1. The QuickBooks invite. In QuickBooks, open Manage users, choose the Accountants tab and invite sam@northwind.example.
2. The card statements for the last three months, through the secure upload: [upload statements](https://example.com/northwind/upload).

If either one is a pain to find, reply and tell me which. There's usually a way around it.

Sam

## Email 2: Reminder two, do it together
Send: on items still missing three days after reminder one
Subject: Want to do the setup together?
Preview: Ten minutes on a call and it's done
CTA: Reply with a time that works for a 10-minute call

Hi Jordan,

The QuickBooks invite still hasn't come through, and the statements aren't in yet. Setup screens can be fiddly, so let's just do it together.

Reply with a time that suits you and I'll call. Ten minutes, and you won't need to find anything in advance.

Sam
```
