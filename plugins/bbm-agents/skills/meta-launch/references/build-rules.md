# Build rules for Meta lead campaigns

Structure advice adapted from coreyhaines31/marketingskills (MIT). API behaviour from hyperfx-ai/marketing-skills (MIT) and Meta's Marketing API documentation. The approval flow follows langchain-ai/paid-media-agent (Apache-2.0). Meta changes often; when the connector's error disagrees with this file, the error wins and this file is wrong.

## 1. Structure by budget

The limit is how many leads a week the budget buys, not how many ideas there are.

- Leads a week at target ≈ daily budget x 7 / target cost per qualified lead. Meta wants ~50 a week per ad set to leave learning. Most small accounts are far below that, so:
- **One campaign, one ad set.** Splitting a small budget across ad sets splits the learning too.
- **Broad targeting.** Country, state or service area, **Advantage+ audience on**. The ads do the targeting. Stack interests only if the owner insists, and say it usually costs more.
- **Ads: up to the ceiling** (daily budget x 14 / (2 x TCPL)). At the ceiling, adding one means removing one.
- **Budget at campaign level** (Meta spreads it across ad sets) when there is more than one ad set; otherwise either level is fine. Never both.
- **Testing campaign:** only when the ceiling is 8+ ads. Then about 80% of budget in the main campaign (proven ads only) and 20% in a testing campaign, same audience. Inside one campaign, proven ads starve new ones, which is why tests get their own budget.
- **Retargeting** (site visitors, video viewers, form openers) only when the warm audience is large enough to spend on (roughly thousands of people a month). Otherwise broad already reaches them.
- **Service area:** use regions, cities or a radius. City and region keys must come from the connector's targeting search, never typed by hand.

### Scaling a winner
Only when: cost per qualified lead at or under target for 2+ weeks, frequency under 3, and 2-3 replacement ads ready. Raise the budget about 20% at a time, a few days apart. If cost per qualified lead goes above 1.5x target after a step, cut back 20-30% and hold two weeks. Increases above ~20% in one step tend to restart learning (practitioner experience, not a Meta rule; `meta.py plan` flags them).

## 2. Lead objective settings

| Setting | Instant form | Website |
|---|---|---|
| Campaign objective | `OUTCOME_LEADS` | `OUTCOME_LEADS` |
| Ad set optimization goal | `LEAD_GENERATION` | `LEAD_GENERATION` |
| Billing event | `IMPRESSIONS` | `IMPRESSIONS` |
| Destination | on-ad (instant form) | website |
| Promoted object | `page_id` | `pixel_id` + `custom_event_type: LEAD` + `page_id` |
| Ad needs | a lead form id | a destination URL with UTMs |

- **Conversion leads** (optimizing for leads that become customers, not just form fills) is available for instant forms once the owner sends CRM stages back to Meta through the Conversions API. It's the biggest lead-quality lever when volume allows. Flag it as a later step; don't set it up without tracking in place (`meta-tracking`).
- **Attribution:** keep one setting across ad sets you compare (the default 7-day click, 1-day view is fine). Never add up conversions from different windows.

## 3. Plan file shapes

```json
{
  "action": "create",
  "title": "Free plan review: broad US",
  "reason": "Launch concepts 1-3 from the 2026-10-01 creative batch",
  "account_id": "act_000000000",
  "campaign": {"name": "Leads | Plan review | 2026-10", "objective": "OUTCOME_LEADS",
               "daily_budget": 30, "special_ad_categories": ["financial_products_services"]},
  "ad_set": {"name": "Broad | Advantage+ audience", "optimization_goal": "LEAD_GENERATION",
             "destination": "instant_form", "lead_form_id": "000000000",
             "targeting": {"countries": ["US"], "advantage_audience": true}},
  "ads": [{"name": "C1 | Broker only calls at renewal | owner video",
           "primary_text": "…", "headline": "…", "description": "…",
           "cta": "GET_QUOTE", "asset": "c1-4x5.mp4"}],
  "measure": "Check on day 7 (delivery) and day 14 (cost per qualified lead vs 40.00 target) with meta-audit.",
  "undo": "Nothing is live. Leave paused or archive in Ads Manager."
}
```

- `update`: `"changes": [{"target": "<id>", "target_name": "<name>", "field": "daily_budget", "before": 30, "after": 36}]`
- `pause`: `"targets": ["<id>", …], "replacement": "<name of the ad taking over>"`
- `activate`: `"targets": ["<campaign id>", "<ad set id>", "<ad ids>…"]`
- Budgets in the plan are in the account currency (30 = $30.00 a day). The API wants cents (3000); the proposal prints both.
- `special_ad_categories`: `[]` (none), or any of `financial_products_services`, `employment`, `housing`, `social_issues_elections_politics`. Unknown → ask; the plan blocks until answered.
- EU or EEA countries in targeting → add `dsa_beneficiary` and `dsa_payor` (who benefits from and who pays for the ads).
- Instant form not built yet → include a `lead_form` draft (intro, questions, thank-you text from meta-creative) instead of `lead_form_id`, and build the form before the ads.

## 4. Gotchas and errors

| Situation | What's true | What to do |
|---|---|---|
| Turning a campaign on | Setting only the campaign to ACTIVE leaves its ad sets and ads paused, so nothing runs | Activate every level listed in the plan (the connector's activate tool, or each object) and read back delivery |
| Budget on campaign and ad set | Once a campaign has a budget, its ad sets can't | Pick one level |
| Advantage+ audience with a narrow age band | Meta rejects a minimum age above 25 or maximum below 65 while Advantage+ audience is on | Widen ages, or turn Advantage+ audience off and say it costs reach |
| Excluding interests, behaviours, demographics | No longer allowed. Only custom audiences can be excluded | Offer a custom-audience exclusion (e.g. existing customers list) |
| "Bid amount required" / "performance goal isn't available" | The account's default bid strategy (a bid cap) blocks lead optimization | Stop. Options for the owner: switch the account default to lowest cost (highest volume), or give a bid cap they choose. **Never** switch to a traffic objective as a workaround: that is not a lead campaign |
| Lifetime budget | Needs start and end dates | Prefer daily budgets for always-on lead gen |
| City/region targeting | Needs Meta's numeric location keys | Look them up with the connector's targeting search |
| Image rejected / wrong account | Images belong to one ad account | Upload to this account first, or use an existing creative from it |
| Special ad category declared | Age, gender, zip-code and lookalike targeting are removed or limited | Broad targeting, let the copy qualify |
| Ad rejected in review | Usually personal attributes, before/after, or claims | Read the rejection reason, fix the copy with meta-creative, new plan |
| Editing a live ad's text or image | Restarts that ad's learning | New ad beside it, then pause the old one once the new one delivers |
