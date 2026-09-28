# How Meta delivery actually works: rules for diagnosis

Read once per session before writing an audit. Each section ends with what it means for advice.

## 1. The learning phase

When an ad set is new or significantly edited, Meta explores who to show it to. Delivery shows "Learning". It exits after roughly **50 optimization events (leads) within 7 days** of the last significant edit. If it can't get there, it shows **"Learning limited"**.

Significant edits (they restart learning): changing targeting, creative or the optimization event; adding a new ad to the ad set; pausing for 7 days or more; changing bid strategy; large budget or bid changes.

What it means:
- Results during learning are unstable and usually more expensive. Caveat every finding on an ad set that is learning.
- Most small lead-gen budgets never reach 50 leads a week. At $40 a lead that takes about $285 a day. "Learning limited" is expected there; it is not a fault to fix. The fix for low volume is fewer ad sets (pool the leads), not more.
- Don't recommend edits to an ad set mid-learning unless something is broken.

## 2. The breakdown effect (the most common wrong advice)

Breakdown reports (placement, age, gender, region, device) show average cost per segment. Meta's system spends toward the lowest **marginal** cost, the cost of the next lead, and a segment's cheap average can hide a rising marginal cost. So Meta often puts more money into a segment with a *higher* average cost, and that is usually correct.

Meta's own example: two placements, $500 budget. Facebook Stories started cheap; its cost per result then rose faster than Instagram Stories'. Meta shifted spend. Final: Instagram Stories $1.46 average on $450, Facebook Stories $1.10 on $50. Cutting Instagram Stories to "save money" would have raised total cost.

What it means:
- **Never** recommend excluding a placement, age band, gender or region on average cost alone.
- If the owner wants to test it, write it as a hypothesis with a measurement plan and a date to check the *overall* cost per lead.
- Evaluate at the level where budget is allocated: campaign budget → campaign; ad set budget with automatic placements → ad set; several ads in one ad set → ad set.

## 3. Normal swings vs real problems

Normal: day-to-day cost swings of 20-30%; weekends vs weekdays; the day after a budget change; the most recent 1-2 days (leads still arriving); learning.

Worth acting on: costs up more than 50% for several days in a row; delivery dropping to near zero; spend rising while leads fall; a drop after no changes at all.

Before calling anything a problem, check in this order: is the window complete; did anything change (budget, status, ads, targeting, the form or landing page, tracking); are the numbers big enough (use spend and clicks before leads); same weekday last week.

## 4. Decision rules (what `meta.py audit` applies)

All in multiples of the owner's target cost per qualified lead (TCPL). Adapted from the Meta decision system in coreyhaines31/marketingskills (MIT); starting points, recalibrate on the owner's own data.

- **Day-7 delivery check:** an ad that got under half an even share of what its ad set spent (ad set spend / ads in it x 0.5) has been deprioritised by Meta. Cut it; the replacement changes hook or visual. An ad alone in its ad set is never judged this way (a small retargeting audience spends little by nature).
- **Data gate:** under 3x TCPL spent → wait. (At true cost = target, 3x TCPL should bring ~3 qualified leads; zero at that spend is unlikely by chance.)
- **No leads at 3x TCPL** → drop the concept, don't iterate it.
- **Qualified rate** (from the owner): under 40% → the ad attracts the wrong people, change the angle and add "who this is for" language; 40-60% → watch; 60%+ → fine. At 40% qualified, the real cost per prospect is 2.5x the cost per lead Ads Manager shows.
- **Cost:** at or under TCPL → winner; up to 1.5x → normal noise; over 1.5x → replace.
- **Ad ceiling:** daily budget x 14 / (2 x TCPL). More ads than that and each one starves. At the ceiling, adding a test means cutting something first.
- **Graduating a winner** (worth more budget): 5+ qualified leads, 60%+ qualified, cost at or under TCPL, running 14+ days, at least one qualified lead in the last 7 days.

## 5. Fatigue

Frequency (average times each person saw the ad) bands:

| Audience | Fine | Warning | Critical |
|---|---|---|---|
| Cold (new people) | under 2.5 | 2.5-4.0 | over 4.0 |
| Warm (site visitors, past leads, engagers) | under 4.0 | 4.0-6.0 | over 6.0 |

Other signs, earliest first: cost per 1,000 impressions (CPM) up 30%+ over two weeks; link click-through rate down 20%+ from its own baseline over a week; relevance rankings "below average"; cost per lead up with nothing else changed.

Local businesses reach their whole audience fast. Plan a fresh ad every 2-4 weeks. When a concept's click rate is 30%+ below its peak or frequency is critical, retire the concept; a new execution of the same idea won't save it.

## 6. Relevance diagnostics

Ads Manager shows three rankings per ad (only after ~500 impressions): quality, engagement rate, conversion rate, each compared with ads competing for the same people. They are diagnostic, not auction inputs.

| Low ranking | Likely problem | Change |
|---|---|---|
| Quality | Looks low-quality or clickbait | Creative |
| Engagement | Doesn't stop the scroll | Hook, first frame, angle |
| Conversion rate | People click but don't convert | Form or landing page, offer-audience fit |
| All three | Wrong message for who is seeing it | Angle and creative together |

## 7. Words to use with the owner

- "Link clicks" (went to the site or form), never bare "clicks" (Meta's "clicks (all)" includes likes and profile taps).
- "Frequency: how many times the same person saw it, on average."
- "Cost per lead" and "cost per qualified lead" are different numbers. Say which.
- "Learning: Meta is still working out who to show it to."
