# Worked examples

For a fictional business: **Northwind Bookkeeping**, monthly bookkeeping for small trade businesses, sender Sam. Every fact below is made up for the example; in real drafts every fact comes from the brand folder or the owner. Each block is a complete draft file and passes `emailkit.py check`.

## Lead magnet delivery

```markdown
---
kind: lead-magnet
business: Northwind Bookkeeping
audience: Trade business owners who downloaded the year-end checklist
trigger: Downloads the year-end books checklist
goal: Get the checklist used and start a conversation
exit: Replies, books a call, or unsubscribes
format: plain
status: draft
---
# Year-end checklist delivery

## Email 1: Deliver the checklist
Send: Day 0, immediately
Subject: Your year-end books checklist
Alt subject: The checklist you asked for
Preview: Start with page one, it takes ten minutes
CTA: Open the checklist

Here's the checklist you asked for:

[Year-end books checklist](https://example.com/checklist)

Start with page one. It's the ten-minute version, and it catches the things that cost the most at tax time.

Over the next two weeks I'll send a few short emails on keeping your books clean without it eating your evenings. No fluff, and you can unsubscribe any time.

One quick question so I send you the right stuff: do you run the business on your own, or do you have a team? Just reply "solo" or "team".

Sam

## Email 2: The one check most people skip
Send: Day 2
Subject: The check most owners skip
Preview: It's on page one of your checklist
CTA: Reply with what you found

Quick one about your checklist.

The item people skip most is matching the bank balance to the books for the last month of the year. It's also the one that causes the most trouble later.

Here's how:

1. Open your bank statement for the last day of the year.
2. Open your books and look at the same account on the same date.
3. If the numbers differ, list every transaction that's in one and not the other.

Most gaps are one of three things: a payment recorded twice, a card fee never entered, or a deposit booked in the wrong month.

Try it and reply with what you found. I read every reply.

Sam
```

## Welcome, first two emails

```markdown
---
kind: welcome
business: Northwind Bookkeeping
audience: Trade business owners who joined the list
trigger: Joins the list or finishes the lead magnet emails
goal: Book a 15-minute call about monthly bookkeeping
exit: Books a call, replies asking about help, or unsubscribes
format: plain
status: draft
---
# Welcome for trade business owners

## Email 1: Why I do this
Send: Day 2
Subject: Why I only work with trades
Preview: It started with my dad's plumbing business
CTA: none

My dad ran a plumbing business for [Client to provide: years] years. He was great at plumbing and dreaded paperwork.

Every spring he'd spend weekends buried in receipts, and every spring the tax bill was a surprise.

That's why Northwind only works with trade businesses. You're great at the work. You shouldn't be doing books at midnight.

Over the next couple of weeks I'll share the simple habits that keep books clean, and what to look for if you ever hand them off.

Sam

## Email 2: The real cost of messy books
Send: Day 4
Subject: What messy books actually cost you
Alt subject: It's not the tax bill
Preview: The bigger cost is the one you don't see
CTA: Reply with the one that sounds like you

Most owners think messy books cost them at tax time. That's the small part.

The bigger cost is deciding blind. You quote a job without knowing your real margin. You hire before you know you can afford it. You apply for a loan and the bank asks for numbers you don't have.

It isn't a discipline problem. It's a system problem. When the books only get touched once a year, they can only tell you about last year.

The fix isn't working harder at it. It's a small monthly routine, which I'll show you in the next email.

Which of those sounds most like you: quoting, hiring, or the bank? Reply with one word.

Sam
```

## Sales, opening email

```markdown
---
kind: sales
business: Northwind Bookkeeping
audience: Subscribers who finished the welcome sequence
trigger: Finishes the welcome sequence
goal: Book a 15-minute fit call for monthly bookkeeping
exit: Books a call, replies, or unsubscribes
format: plain
status: draft
---
# Monthly bookkeeping offer

## Email 1: Introduce monthly bookkeeping
Send: Day 0
Subject: Want me to just do your books?
Preview: Here's how monthly bookkeeping works with us
CTA: Book a 15-minute fit call

You've seen the monthly routine. Some of you will run it yourselves, and that's great.

Others have told me the same thing: "I get it, I just don't want to be the one doing it."

That's what Northwind's monthly bookkeeping is for. Each month we:

1. Reconcile every account
2. Categorize every transaction
3. Send you a one-page report you can read in five minutes

You get clean numbers by the 10th of every month, and you never touch a receipt pile again.

It's [Client to provide: monthly price or range] a month, and there's no long contract.

If you want to see if it fits your business, grab 15 minutes here:

[Book a fit call](https://example.com/book)

Sam
```
