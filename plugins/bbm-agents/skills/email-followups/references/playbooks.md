# Follow-up playbooks

One section per kind: the touches, when each goes, its one job, what goes in it, and one example written for a fictional firm, Northwind Bookkeeping (sender Sam). The examples are in the shared draft format and pass `emailkit.py check`. They show the shape; the owner's voice file decides greeting, sign-off and wording.

Day counts start at the trigger (the call, the missed slot, the proposal sent, the last message). Any reply stops the sequence. At least 2 days between touches; at most 5 touches including the breakup.

## Angles that count as "something new"

Rotate through these so no two touches do the same job:

- **Answer the question they probably have** (what happens in week one, how long it takes, what they need to do).
- **Something useful that asks nothing:** a tip, a checklist, a warning about a real seasonal issue, a short answer to a problem they mentioned.
- **Proof:** a real result for a similar client, from the brand files or the owner. Never invented, never exaggerated.
- **A decision question:** "Is this still a priority this quarter?" Easy to answer, no pressure.
- **A way to say not now:** offer to come back at a date they pick.
- **The clean close:** the breakup.

## call-recap

Trigger: a sales or discovery call just ended. Source: the owner's call notes or transcript. No notes, no recap; ask for them.

| Touch | Send | Job | Include |
|---|---|---|---|
| 1 | Day 0, within a few hours | Show you listened and lock the next step | Their problem, their goal and what is at stake, in their words where the notes have them. What was agreed. Who does what by when. The one next step and whose it is. |
| 2 | Day 5, only if the next step hasn't moved | Make the next step easy | The next step restated, plus one new thing: an answer to a question they raised on the call, or a way to make their part smaller. |

After touch 2, a proposal sent moves to `proposal`; silence moves to `gone-quiet`.

Notes:
- Quote them only when the notes have the words. Paraphrase otherwise, and never add a pain they didn't mention.
- Keep the recap forwardable: someone who wasn't on the call should understand it.
- If a proposal was promised, the recap says when it arrives. It does not include the proposal.

```markdown
---
kind: call-recap
business: Northwind Bookkeeping
audience: Priya, owner of Cedar Row Landscaping, after a discovery call
trigger: Discovery call held Tuesday afternoon
goal: Priya sends last year's statements so Sam can scope the cleanup
format: plain
status: draft
---
# Recap for Priya, Cedar Row Landscaping

Notes for the owner: the quote and the second-crew plan come from your call notes. Price stays out until the proposal, as you said on the call.

## Email 1: Recap the call and lock the next step
Send: Day 0, within a few hours of the call
Subject: Notes from today and the one next step
Preview: What you told me, what we agreed, who does what
CTA: Send last year's bank and card statements by Friday

Hi Priya,

Thanks for the time today. Here's what I heard, so we're both working from the same page.

Where things are: the books are about eight months behind, and in your words, "I find out how we did when my accountant calls in March."

What you want: each month's numbers by the middle of the next month, so you can decide on a second crew before spring.

What we agreed:
- You send last year's bank and card statements by Friday.
- I review them and send a cleanup plan with a fixed price by next Wednesday.
- If the plan works for you, we set up the monthly close from there.

The next step is yours: the statements. The upload link keeps them private: [upload statements](https://example.com/upload)

Sam
```

## no-show

Trigger: a booked call they didn't join. Assume something came up.

| Touch | Send | Job | Include |
|---|---|---|---|
| 1 | Day 0, an hour or two after the missed slot | Rebook with zero guilt | One friendly line, two specific times, the booking link. No "I waited", no "we had a call booked". |
| 2 | Day 2 or 3 | Give them a reason to rebook | Something useful tied to why they booked: the one question you'd have asked, a short tip, what the call would cover. Then the link. |
| 3 | Day 7 | Close the loop | Say you'll stop, leave the booking link, and the door open. |

```markdown
---
kind: no-show
business: Northwind Bookkeeping
audience: Marcus, who booked a 20-minute intro call and didn't join
trigger: Missed the intro call booked for Thursday at 10:00
goal: Rebook the intro call
format: plain
status: draft
---
# No-show, Marcus

## Email 1: Easy reschedule, no guilt
Send: Day 0, about an hour after the missed slot
Subject: Another time for our call?
Preview: Two options, or pick your own
CTA: Reply with a time or use the booking link

Hi Marcus,

Looks like today didn't work out. No problem, something always comes up.

Would either of these suit you?
- Monday at 9:30
- Tuesday at 2:00

Or pick any open slot here: [book a time](https://example.com/book)

Sam
```

## proposal

Trigger: a proposal or quote was sent and nothing came back. Day 0 is the day it went out.

| Touch | Send | Job | Include |
|---|---|---|---|
| 1 | Day 2 | Make it easy to say yes or ask | "Anything unclear?" plus one useful addition: the answer to the question most people have at this point. A short summary they can forward to whoever else decides. |
| 2 | Day 5 | Add proof | One real result or example for a similar client, from the brand files or the owner. No real proof yet: send a useful resource instead and mark the gap for the owner. |
| 3 | Day 10 | Ask the decision question | "Is this still a priority for this quarter?" with a simple way to say not now. If a real start date or price hold is ending, say so plainly. |
| 4 | Day 17 | Breakup | See `breakup`. |

**More than one decision-maker** (a partner, a spouse, a board, an office manager and a practice owner): give them something to forward. Three or four lines in plain words: the problem, what you'll do, the price as written in the proposal, when it starts. Put it in touch 1 as a quoted block. It must match the proposal exactly.

```markdown
---
kind: proposal
business: Northwind Bookkeeping
audience: Dana, operations manager at Harbor Street Dental, who got the proposal Monday
trigger: Proposal sent Monday, no reply yet
goal: A yes, a question, or a clear not now on the monthly bookkeeping proposal
format: plain
status: draft
---
# Proposal follow-up, Harbor Street Dental

Notes for the owner: the first-month steps come from offers.md. The price in the summary is the one in the proposal you sent.

## Email 1: Answer the likely question and give Dana a version to forward
Send: Day 2, morning
Subject: (reply in the proposal thread)
Preview: What the first month looks like, plus a short version to forward
CTA: Reply with a question, or forward the summary

Hi Dana,

The question most practices ask at this point: what does the first month look like? Week one we connect your bank feeds. Week two we tidy up last quarter. By the end of the month you have your first report.

If Dr. Lee needs to sign off, here's a short version you can forward:

> Northwind takes over the practice's monthly bookkeeping for $650 a month, starting with a cleanup of last quarter. First report at the end of month one. Full proposal is in Dana's email.

Is anything in the proposal unclear, or worth changing?

Sam
```

## gone-quiet

Trigger: a warm lead stopped answering, either before a call was booked or partway through a conversation. Day 0 is when the owner decides to follow up (usually five or more business days of silence after their last message).

| Touch | Send | Job | Include |
|---|---|---|---|
| 1 | Day 0 | Reconnect through their goal | What they said they wanted, in their words, and a small new reason to talk. A low-friction ask ("reply yes and I'll send two times"). |
| 2 | Day 4 | Be useful, ask nothing | A tip or resource that helps whether or not they buy. |
| 3 | Day 10 | Change the angle | A real result for a similar client, or a direct question: "Did this drop down the list, or did you solve it another way?" |
| 4 | Day 18 | Breakup | See `breakup`. |

Notes:
- **Before a call** the relationship is thin: keep every touch under about 100 words and the ask tiny.
- **Mid-conversation** (they asked questions, then stopped): start with the thing they were last deciding, and answer anything left open.
- If they were referred, name the referrer only if the referrer said that's fine.

```markdown
---
kind: gone-quiet
business: Northwind Bookkeeping
audience: Jordan, owner of a small heating and cooling company, who emailed twice then went quiet before booking a call
trigger: No reply for two weeks after asking about monthly bookkeeping
goal: Book an intro call
format: plain
status: draft
---
# Gone quiet, Jordan

## Email 1: Reconnect through what Jordan said he wanted
Send: Day 0, Tuesday morning
Subject: Getting your Sundays back
Preview: One thing worth doing this month either way
CTA: Reply yes and Sam sends two call times

Hi Jordan,

When we last emailed, you said you wanted to stop doing the books on Sunday nights.

Something worth doing this month whether or not we ever work together: save every card statement since January into one folder now. It's the step that eats the most time when tax season arrives.

If you'd still like the whole thing off your plate, reply "yes" and I'll send two times for a short call.

Sam
```

## breakup

Trigger: the last touch of any sequence, or the owner wants to close a stalled deal. One email. Its job is to end the chase cleanly, which is also the touch most likely to get an answer.

Include:
- The plain situation in one line, no blame ("I haven't heard back, so I'll assume the timing isn't right").
- That this is the last note on this topic.
- An easy way back: a one-number reply (1 interested, 2 not now, 3 close it out), or one line saying they can reply any time.
- Optional: one small useful thing, if it genuinely helps them.

**Honor it.** After the breakup, the sales follow-up is over:
- A reply of 1 → `reply`. A reply of 2 → ask for a month, and suggest a reminder task to the owner for that date. A reply of 3 or silence → closed-lost; record the reason if known.
- Nurture only with consent: they go on a newsletter or marketing list only if they already opted in, or they say yes when asked. Otherwise no list.
- Never restart the same sequence. A later personal note needs a genuinely new reason and the owner's call.

```markdown
---
kind: breakup
business: Northwind Bookkeeping
audience: Dana, operations manager at Harbor Street Dental, after three proposal follow-ups with no reply
trigger: Proposal sent 17 days ago, three follow-ups, no reply
goal: A clear answer or a clean close
format: plain
status: draft
---
# Breakup, Harbor Street Dental

## Email 1: Close the loop and leave the door open
Send: Day 0, morning
Subject: Closing the loop on the bookkeeping proposal
Preview: Last note from me on this
CTA: Reply 1, 2 or 3

Hi Dana,

I haven't heard back on the proposal, so I'll assume the timing isn't right and stop following up on it.

To make it easy, a one-number reply works:
1. Still interested, let's talk
2. Not now, check back in the new year
3. Not for us, please close it out

Either way, thanks for considering Northwind.

Sam
```

## reply

Trigger: they wrote back. Stop any running sequence first. Then pick the bucket in `replies.md` and draft one reply.

Rules: answer their actual question in the first line; keep it shorter than their email; match their tone and greeting; if the ask is a call, two specific times plus the booking link; one ask.

```markdown
---
kind: reply
business: Northwind Bookkeeping
audience: Marcus, who replied to the reschedule email with a question
trigger: Marcus asked whether Northwind works with his accounting software
goal: Answer the question and book the call
format: plain
status: draft
---
# Reply to Marcus

## Email 1: Answer the question first, then two times
Send: Day 0, within a few hours of his reply
Subject: (reply in his thread)
Preview: Short answer, yes
CTA: Pick one of the two times

Hi Marcus,

Yes, we work in Xero every day, so there's nothing to switch.

Does Monday at 9:30 or Tuesday at 2:00 work for the call? If neither does, grab a slot here: [book a time](https://example.com/book)

Sam
```

## one-off

Trigger: a situation the owner describes that isn't a sequence: sending what was promised at an event, a note after a referral intro, a reminder that a quoted price holds until a real date, a thank-you after a no that was handled well.

Steps:
1. Ask what happened, what they want the person to do next, and what was promised.
2. Borrow the closest kind's rules (a promised resource is like touch 2 of `gone-quiet`; a deadline note is like touch 3 of `proposal`).
3. One email, one job, one ask. If it wants a follow-up later, say so in the notes and let the owner decide.

```markdown
---
kind: one-off
business: Northwind Bookkeeping
audience: Alex, a café owner Sam met at a chamber of commerce breakfast
trigger: Sam promised to send the month-end checklist
goal: Deliver the checklist and open the door to a call
format: plain
status: draft
---
# One-off, Alex

## Email 1: Send what was promised at the breakfast
Send: Day 0, next weekday morning
Subject: The month-end checklist I mentioned
Preview: From the chamber breakfast on Wednesday
CTA: Reply if a second look at the books would help

Hi Alex,

Good to meet you at the chamber breakfast on Wednesday. Here's the month-end checklist I mentioned: [month-end checklist](https://example.com/checklist)

The first page is the part that matters for a café: matching card sales to what actually lands in the bank.

If a second pair of eyes on your books would help at some point, reply here and we'll find a time.

Sam
```
