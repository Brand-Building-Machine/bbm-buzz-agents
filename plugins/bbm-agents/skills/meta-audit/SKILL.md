---
name: meta-audit
description: Diagnose the owner's Facebook and Instagram (Meta) lead ads. Reads the account through Meta's own ads connector, or an Ads Manager export, and says in plain words which ads to keep, cut, fix or scale, why cost per lead moved, and whether the budget and structure fit. Lead generation focus (forms, calls, bookings), judged on cost per QUALIFIED lead. Use when the owner says "how are my Facebook ads doing", "why did my cost per lead go up", "which ads should I turn off", "audit my Meta ads", "is my ad account set up right", or pastes an Ads Manager export. Read-only; changes go through meta-launch.
---

# meta-audit

Tell the owner what their Meta lead ads are really doing and what to do next. `scripts/meta.py` does the arithmetic; you do the reading. Never do maths over raw rows yourself.

The script is `scripts/meta.py`, relative to this skill's folder. Run it with `python3` on macOS/Linux, `python` or `py` on Windows. The other Meta skills (`meta-creative`, `meta-launch`, `meta-tracking`) use the same script.

## Before you start

1. `meta.py paths [--business <name>]` shows where reports go and whether the ads profile exists. No config → run `workspace-config` first.
2. **The ads profile** (`meta-ads.json`, next to the brand files) holds what only the owner knows: ad account, Facebook Page, what a *qualified* lead means, the target cost per qualified lead, and the most they will spend a day. No profile → `meta.py profile init`, then fill it in **with the owner** (step "Set the target" below). Audits still run without it; verdicts just say "set a target".
3. Read `offers.md` and `brand-bible.md` if present, so you know what a lead is worth and who the ads should attract.

## Get the numbers

**Option A: Meta's ads connector (preferred).** Meta's official connector (`https://mcp.facebook.com/ads`) reads the account live with the owner's own Meta login. Setup and troubleshooting: `references/connector.md`. Use its account, campaign/ad set/ad and insights tools (names like `ads_get_ad_accounts`, `ads_insights_*`; use whatever the connector lists). Pull, at **ad level**, for the last 14 complete days (and the prior 14 for comparison): ad name, ad set name, campaign name, delivery status, amount spent, leads, impressions, reach, frequency, link clicks. Save the rows as JSON in the reports folder, then run the script on that file.

**Option B: an export.** Ads Manager → Ads tab → pick the date range → Reports → Export table data (CSV). Ask for these columns: Ad name, Ad set name, Campaign name, Ad delivery, Amount spent, Leads, Impressions, Reach, Frequency, Link clicks. This works on any machine with no connector.

**Qualified leads are the number that matters.** Meta counts form fills; the owner knows which ones were real prospects. Ask: "Of the leads from each ad, roughly how many were real prospects?" Add a `Qualified leads` column (or field) with their answer. If they don't know, run without it and say the verdicts use raw leads.

## Run it

```
meta.py audit <file> [--tcpl 40] [--daily-budget 50] [--days 14] [--business <name>] [--json]
```

It reads the target from the profile when you don't pass it. Pass `--daily-budget` as the **actual** daily budget of the main campaign (from the connector or the owner); it sets how many ads the budget can feed. Without it the script uses the profile's ceiling and says so in the numbers. The day-7 delivery check needs no budget: it compares each ad with the others in its own ad set. It gives each row one verdict, plus account notes (learning volume, how many ads the budget can feed):

| Verdict | Meaning | What you tell the owner |
|---|---|---|
| `kill` | No delivery, or by day 7 under half an even share of what its ad set spent. Meta has already decided | Turn it off; the replacement should change the hook or the visual (the audience never got far enough for copy to matter) |
| `wait` | Spent under 3x the target cost per lead | Too early to judge. Leave it |
| `swap` | Enough spend and: no leads, or under 40% qualified, or over 1.5x target | Replace it. No leads → new concept. Wrong people → new angle, add "who this is for" language. Too expensive → offer or audience |
| `monitor` | Within 1.5x target, or 40-60% qualified | Normal noise. Look again next week |
| `winner` | At or under target (and 60%+ qualified when known) | Keep. Candidate for more budget (via meta-launch) |
| `check` | The export's "Results" are not leads | Re-export with the Leads column |
| `info` | Breakdown rows (placement, age, gender, region) | Context only, see below |

Before writing anything, read `references/diagnosis.md` once per session. It holds the rules that stop wrong advice: the learning phase, the breakdown effect, normal vs worrying swings, fatigue, and relevance diagnostics.

## Hard rules

- **Never recommend cutting a placement, age band, gender or region because its average cost is higher.** Meta spends toward the cheapest *next* lead, not the lowest average. Frame any such idea as a test with a measurement plan, never as a directive.
- **Judge at the level where the budget lives.** Campaign budget → judge the campaign. Ad set budget → judge the ad set. Never call an ad "bad" inside an ad set that is still learning without saying so.
- **Small numbers are not trends.** 2 leads to 4 is not "+100%". Quote the base. Day-to-day swings of 20-30% are normal. Call something a trend only if it holds across two full windows.
- **Missing is not zero.** A metric the export didn't include is "not measured".
- **Editing a running ad resets its learning.** Recommend launching a new ad beside it, never editing a winner.
- **Never pause without a replacement ready**, unless the ad is spending with no leads at all.
- Attribution settings (7-day click, 1-day view, and so on) change the lead count. Don't compare numbers pulled under different settings.

## Set the target (first run with a new owner)

Target cost per qualified lead (TCPL) anchors everything. Get it from their numbers, not a benchmark:

- "What can you afford to pay to win one customer?" and "Out of 10 real prospects, how many become customers?"
- `meta.py tcpl --cost-per-customer 600 --lead-to-customer 0.25 --daily-budget 50` → TCPL, when an ad can be judged, how many ads the budget can feed, and whether the account will ever leave learning.
- No history at all: use that answer and replace it with (last 30 days' cost per qualified lead x 0.8) after a month.
- Also confirm: `max_daily_budget` (hard ceiling, meta-launch refuses plans above it), `qualified_lead_means` (one sentence), `special_ad_categories` (credit/loans/insurance/financial services, jobs, housing, social issues/politics, or none).

Write their answers into `meta-ads.json` after they confirm, then `meta.py profile check`.

## Write the report

Save to `<reports folder>/YYYY-MM-DD-audit-<account or business>.md`:

```
# Meta ads check: <business> (<date range>)
<One line: spend, leads, cost per lead, cost per qualified lead if known, vs target.>
<One line: the single most important thing.>

## Do this week
1. <Action> | Why: <evidence with numbers> | Who: <owner / us via meta-launch / their designer>
... (max 5)

## Ads
| Ad | Verdict | Spend | Leads | Cost per lead | Why |

## Account health
Budget vs ads running | learning volume | fatigue | tracking (flag and suggest meta-tracking if leads look wrong)

## Not checked
<what this could not see: qualified leads, CRM outcomes, tracking quality, anything the export lacked>
```

## Report to the owner

A top-level message: the business and date range, the one-line verdict, the top 3 actions in order and who does each, the path to the full report, and "from meta-audit". Offer the next skill that fits: new ads needed → `meta-creative`; a change to make → `meta-launch`; leads look wrong or missing → `meta-tracking`.

Plain words, first time for every term ("frequency, how many times the same person saw the ad on average"). No jargon the owner didn't use first.

## Limits

Read-only. This skill never changes the ad account; changes are planned and approved in `meta-launch`. Never invent numbers, benchmarks or competitor figures; industry averages only when labelled as rough and sourced.
