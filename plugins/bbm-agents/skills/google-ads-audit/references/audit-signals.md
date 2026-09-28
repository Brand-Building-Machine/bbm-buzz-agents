# Audit signals

What `gads.py audit` checks, the thresholds, and how to judge the edge cases. Scoring: PASS = full points, WARN = half, FAIL = none; ASK, UNKNOWN, NA and INFO are left out and the remaining areas are re-weighted. Grade A ≥ 90, B ≥ 80, C below. Weights and the pass/warn/fail pattern follow Optmyzr's audit (Apache-2.0).

| # | Area | Weight |
|---|---|---|
| 1 | Account & settings | 5 |
| 2 | Conversion tracking | 12 |
| 3 | Campaign structure | 7 |
| 4 | Performance Max & other channels | 8 |
| 5 | Budgets & spend | 7 |
| 6 | Bidding | 8 |
| 7 | Targeting | 5 |
| 8 | Audiences | 6 |
| 9 | Keywords | 7 |
| 10 | Quality Score | 10 |
| 11 | Search terms & negatives | 10 |
| 12 | Ads | 8 |
| 13 | Assets | 4 |
| 14 | Landing pages | 3 |

"Search campaigns" below means enabled Search campaigns. "Per month" figures scale the fetched period to 30.4 days.

## 1 Account & settings
- **1.1 Shared negative list on non-brand Search campaigns.** PASS 80%+ covered, WARN some, FAIL none. Brand campaigns are exempt (a generic list can block brand searches).
- **1.2 Auto-tagging on.** FAIL if off: Analytics and offline imports can't tie leads to clicks.
- **1.3 Time zone and currency** (info). Can't be changed later.
- **1.4 What is live now** (info). Share of the period's spend in campaigns now paused. Recommend for the live account.

## 2 Conversion tracking
"Primary" means primary for the goal **and** included in the Conversions column (what bidding uses).
- **2.1 Primary conversions are real outcomes.** FAIL none, or micro-events (page view, engagement, add to cart, begin checkout) as primary on a results account. WARN more than 5 primaries, or a store counting calls/directions as primary.
- **2.2 Conversions recorded.** FAIL if spend but zero conversions: tracking is broken or nothing converts. Either way, fix before anything else.
- **2.3 Counting method.** WARN leads counted "every" (one person, three form fills = three leads) or purchases counted "one".
- **2.4 No double counting.** WARN when one category has primary actions from different sources (tag + GA4 import, Smart campaign + regular).
- **2.5 Values.** Stores: FAIL no conversion value. Leads: WARN when every lead is worth the same token amount.
- **2.6 Offline / CRM conversions** (leads). WARN without an import of qualified leads or deals.
- **2.7 Enhanced conversions** (ask). **2.8 Consent mode** (ask; only EU/EEA/UK).

## 3 Campaign structure
- **3.1 Brand vs non-brand** (needs brand terms). FAIL when a campaign mixes brand and non-brand keywords (brand under 80% of its keywords). WARN no brand keywords at all.
- **3.2 Campaign types fit the goal.** FAIL store without live Shopping or Performance Max. WARN Performance Max over 70% of a lead-gen budget, or awareness channels over half the spend on a results account.
- **3.3 Enough data per campaign.** WARN two or more smart-bidding Search campaigns under 15 conversions/month: merge them.

## 4 Performance Max & other channels
- **4.1 Asset group strength.** PASS 80%+ Good/Excellent, WARN 50-80%, FAIL under 50%.
- **4.2 Brand exclusions** (ask). **4.3 Placement exclusions** (ask, when Display/Demand Gen/PMax run).

## 5 Budgets & spend
- **5.1 Profitable campaigns not held back.** Campaigns with 3+ conversions at or under target (or the account average): worst "lost impression share (budget)" PASS < 10%, WARN 10-25%, FAIL > 25%. The fix is moving budget from waste, not only adding budget.
- **5.2 Shared budgets.** FAIL a shared budget over 5+ campaigns or including brand with others; WARN 3-4.
- **5.3 No campaign spending without results.** FAIL any enabled campaign with zero conversions and spend above 3 × CPA (or 5% of account spend). Monthly impact = its spend.

## 6 Bidding
- **6.1 Strategy fits the data.** Misaligned = Enhanced CPC, or manual/click bidding on a campaign with 15+ conversions/month. PASS under 10% of Search spend, WARN up to 50%, FAIL above.
- **6.2 Targets have data behind them.** CPA/ROAS targets: PASS 30+ conversions/month, WARN 15-30, FAIL under 15.
- **6.3 Targets are realistic.** WARN a target CPA below 70% of actual: it chokes delivery.
- **6.4 Left alone to learn.** Campaign/budget/bidding changes in 14 days: WARN 3-5 on one campaign, FAIL more.

## 7 Targeting
- **7.1 Presence, not presence-or-interest.** WARN some, FAIL half or more.
- **7.2 Search stays on Search.** FAIL Display Network on a Search campaign; WARN Search Partners on.
- **7.3 Every campaign has locations.** FAIL any without (shows worldwide).
- **7.4 Ad schedule** (leads). WARN none; ask whether leads get answered 24/7.

## 8 Audiences
- **8.1 Customer list.** PASS a Customer Match list with 1,000+ matched on Search; WARN smaller or none.
- **8.2 Customers excluded from prospecting** (ask, leads).

## 9 Keywords
- **9.1 One home per keyword.** Same text + match type in 2+ ad groups: WARN under 1% of spend, FAIL above.
- **9.2 Broad only with smart bidding.** FAIL broad keywords in manual/click-bid campaigns.
- **9.3 Dead or disapproved.** FAIL any disapproved; WARN over 5% of enabled keywords with no impressions.

## 10 Quality Score
Over keywords with spend and a score.
- **10.1 Spend-weighted Quality Score.** PASS ≥ 7, WARN 5-7, FAIL < 5.
- **10.2 Spend on score ≤ 4.** PASS < 10%, WARN 10-25%, FAIL > 25%.
- **10.3 Weak parts on the top 20 keywords.** Share with any "below average" part: PASS 0, WARN ≤ 20%, FAIL more. The fix depends on the part: expected click rate → headlines; ad relevance → tighter ad groups; landing page → faster, matching page.

## 11 Search terms & negatives
- **11.1 Spend on searches that never convert.** Searches costing at least max(10, half the CPA) with zero conversions, as a share of search-term spend: PASS < 5%, WARN 5-15%, FAIL > 15%. The evidence also gives all non-converting spend including cheap searches. You review the list before calling it waste.
- **11.2 Lin-Rodnitzky ratio** = all-search CPA ÷ converting-search CPA. 1.5-2.0 healthy; 2-3 or under 1.5 WARN; over 3 FAIL. Not scored under 30 conversions from search terms.
- **11.3 Every Search campaign has negatives** (campaign, ad group or shared list).

## 12 Ads
- **12.1 Ad strength.** Good/Excellent share: PASS 80%+, WARN 60-80%, FAIL under 60%.
- **12.2 Ads per ad group.** FAIL an ad group with keywords but no live responsive search ad; WARN under 70% of ad groups with 2+ ads.
- **12.3 Headlines and descriptions.** PASS median 10+ headlines and 3+ descriptions with under 20% of ads below 8 headlines; FAIL median under 7 headlines, under 3 descriptions, or half the ads under 8.
- **12.4 Copy specific to each ad group.** Headlines found in 40%+ of ad groups, as a share of the median ad's headlines: PASS ≤ 20%, WARN ≤ 40%, FAIL more. Two or three shared brand lines are fine.
- **12.5 No disapproved or retired ads.** FAIL disapproved ads or 6+ old text ads; WARN limited approvals or any old text ads.

## 13 Assets
Campaign-level assets override account-level ones; the script counts whichever applies.
- **13.1 Sitelinks** 4+ on every Search campaign. **13.2 Callouts** 4+ and a structured snippet. PASS all, WARN half, FAIL fewer.
- **13.3 Call asset** (leads) or **image assets** (others). WARN if missing.

## 14 Landing pages
- **14.1 Matching pages, not the homepage.** WARN non-brand ad groups sending clicks to the homepage.
- **14.2 Pages load** (with `--check-urls`, top 10 live pages by spend). FAIL any broken or redirected off-site; WARN over 4 seconds for the HTML. Compare each page's title and H1 with its ads yourself.

## Not covered by the API
Call recordings and call quality, which leads became customers (unless imported), the site's checkout or form flow, Merchant Center feed health, Local Services Ads, auction insights. Say so in the report and ask when it matters.
