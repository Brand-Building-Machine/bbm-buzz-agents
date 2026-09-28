# Strategy playbook

How to design a Google Ads account for a small or mid-size business. Rules of thumb, not laws: when the owner's own data says otherwise, the data wins. Numbers here are practitioner starting points; the first 30 days of real data replace them.

## The intent ladder: where money goes first

Open spend one rung at a time. Each rung earns budget only after the one below converts.

1. **Brand**: people searching your name. Cheapest clicks, best conversion. Always on, small capped budget, its own campaign.
2. **High-intent non-brand**: ready to buy ("roof repair denver", "employee benefits broker for small business"). Most of the budget lives here.
3. **Competitor**: "<competitor> alternative". Higher cost, lower conversion; later, with a comparison page.
4. **Problem-aware**: has the problem, isn't shopping ("why is my roof leaking"). Only after 1-2 work.
5. **Awareness**: Display, YouTube, Demand Gen. Last, with spare budget.

Search captures demand that already exists. If almost nobody searches for it, Search is the wrong tool; say so.

## Account structure

- **Fewer, better-fed campaigns.** Smart bidding learns from conversions. A campaign that can't get ~15 conversions a month is starving; merge it with a sibling that shares goal and area.
- **Split campaigns only when something real differs**: budget, location, bidding goal, or brand vs non-brand. Different services with the same economics can be ad groups in one campaign.
- **Brand gets its own campaign and budget.** In a shared budget, cheap brand clicks eat everything.
- **Themed ad groups, not one keyword per group.** 5-15 closely related keywords that one ad and one landing page can answer. Two keywords that need different pages or promises go in different groups.
- **One home per keyword.** The same keyword and match type in two ad groups competes with itself.
- **Naming**: `<Type> | <Theme> | <Geo>` (e.g. `Search | Roof Repair | Denver`). Consistent names make reports readable.

## Keywords and match types

- Seed from **how buyers describe the problem**: the owner's customer phone language, reviews, service + city, "near me", urgency words ("emergency", "same day"), comparison words ("best", "top rated").
- Tag each keyword by intent: buy-now, comparing, researching. Launch buy-now and comparing.
- **Start with phrase and exact.** Exact `[roof repair denver]` still matches close variants; phrase `"roof repair"` matches searches containing the meaning. Add **broad** only when all three hold: smart bidding is on, the campaign gets 30+ conversions a month, and a solid negative list exists. Broad without them is a donation.
- Low-volume keywords ("0-10 searches") aren't useless: planner volumes are rounded and local. Keep clearly high-intent ones; drop vague ones.
- Bid ranges from Keyword Planner ("top of page bid low-high") are what advertisers paid for the top spots. Use the middle of the range as a planning CPC, not the low end.

## Negative keywords

Apply at build time, from evidence:
- **Clear non-customers** for this business: jobs, careers, salary, hiring, training, course, certification, DIY, free, cheap (only if they don't compete on price), used, parts (for service businesses), definitions ("what is", "meaning").
- **Category collisions**: meanings the category shares with something unrelated.
- **Out-of-area** place names that the planner surfaced.
- **Brand as a negative in non-brand campaigns** so brand searches land in the brand campaign.

Mechanics: a negative broad blocks searches with all its words in any order ("free trial" does not block "free"). Negative phrase blocks that phrase in order. Negative exact blocks only that exact search. Negatives do not match close variants: add plurals and misspellings yourself.

Don't over-negative. Every negative narrows reach; an uncertain term deserves data first. After launch, the weekly search-terms review adds negatives from real searches.

## Bidding by conversion volume (per campaign, per month)

| Conversions/month | Strategy |
|---|---|
| 0-15, new account | Maximize Clicks with a max CPC cap, or Manual CPC, for the first 2-4 weeks to gather data; or Maximize Conversions from day one if tracking is solid and the budget allows ~15+/month |
| 15-30 | Maximize Conversions (no target) |
| 30+, steady | Add a target CPA at or slightly above the last 30 days' actual |
| Real order values tracked, 30+ | Maximize Conversion Value, then target ROAS near actual |

Move targets 10-15% at a time, 1-2 weeks apart. Every change restarts learning. A campaign losing impressions to budget while converting under target should get more budget before any bid change. Enhanced CPC is retired; don't use it.

## Budget math

- Monthly = daily × 30.4. Google may spend up to 2× the daily budget on a single day and balances over the month.
- Clicks = monthly ÷ planning CPC. Conversions = clicks × conversion rate. Cost per conversion = CPC ÷ conversion rate.
- **Break-even cost per lead** = average sale (or gross profit) × close rate. Cost per sale for stores = order value × margin.
- Budget for 15 conversions a month = 15 × CPC ÷ conversion rate. If the owner's budget is well below it, narrow the plan (one service, fewer towns, business hours only) rather than spreading thin.
- Starting conversion rates when you have no data (label as assumptions): local service lead forms and calls 5-10%, professional services 3-7%, B2B 2-5%, e-commerce 1-3%. Replace with actuals after 30 days.

## Settings for every new Search campaign

- Networks: **Google Search only**. Search Partners off until Search is proven; Display Network always off on Search campaigns.
- Locations: the service area, with **"Presence: people in or regularly in your locations"** (not the default presence-or-interest).
- Language: the languages customers use (it keys off their Google interface language).
- Ad schedule: match when calls and forms get answered; lower bids or pause outside those hours.
- Auto-tagging on. Link GA4 if the site has it.
- Build **paused**; launch only after a test conversion is recorded.

## Conversion tracking (set up first)

- **Primary** (what bidding optimizes): 1-3 real outcomes. Lead form submit, qualified call (60+ seconds), booked appointment, purchase.
- **Secondary** (observe only): page views, clicks on phone numbers without a call, add to cart, directions, time on site.
- Counting: leads **one** per click; purchases **every**.
- **Value**: purchases pass the order value; leads get an average value (average sale × close rate) so bidding can prefer better leads.
- **Enhanced conversions** on the main form or purchase.
- **Calls**: Google forwarding numbers or a call-tracking tool, counting calls over ~60 seconds.
- **Offline conversions**: when leads go into a CRM, import qualified leads and closed deals back to Google with the click ID. The single biggest lever for lead quality.
- **Consent mode** if they advertise in the EU/EEA/UK.
- Duplicate counting check: the same outcome tracked two ways (Google Ads tag and GA4 import) → one primary, the other secondary.

## Responsive search ads

- 10-15 headlines (30 characters max), 4 descriptions (90 max), 2 display paths (15 max each).
- 2-3 headlines contain the ad group's main keyword. Others cover: the service, proof (years, licences, reviews), the offer, speed/availability, location, the call to action.
- Each headline must make sense on its own and next to any other.
- Pin only what must be pinned (a legal line, the brand). Every pin reduces what Google can test.
- One or two ads per ad group; different angles, not word swaps.
- Google policy: no exclamation marks in headlines, no excessive caps, no gimmicky punctuation, claims must be supported on the landing page, superlatives ("best") need proof.

## Assets

- **Sitelinks**: 4-8 to real, distinct pages (services, about, reviews, contact, financing). Text 25 characters, two description lines 35 each.
- **Callouts**: 4-8 short differentiators, 25 characters each ("Licensed and Insured", "Free Estimates").
- **Structured snippet**: header (Services, Types, Brands, Destinations...) with 3-10 values.
- **Call asset** for any lead business; **location asset** (linked Google Business Profile) for local businesses; **image assets**, **business name and logo** for everyone.

## Landing pages

- One page per ad group theme, the headline echoing the search and the ad's promise.
- One job and one call to action; phone number clickable on mobile; form short enough for the lead quality wanted.
- Proof above the fold: reviews, licences, guarantees, photos of real work.
- Fast on mobile. Missing pages go on the owner's to-do list (SEO Desk's `seo-page` can draft them).

## By business type

- **Local services** (trades, clinics, brokers, agencies with an office): Search first; call asset and location asset; tight radius; business-hours schedule; calls often matter more than forms. Local Services Ads (Google Guaranteed/Screened) are a separate product worth mentioning if their category qualifies.
- **Professional / B2B** (insurance brokers, accountants, consultants): lower volume, higher value per lead, long sales cycles. Keep structure minimal, value leads properly, and prioritise offline conversion import from the CRM. Expect 60-180 days from click to deal.
- **E-commerce**: Merchant Center feed quality first (titles, images, prices, GTINs). Shopping or Performance Max with the feed, plus brand Search. Track purchase value; bid on value.
- **Regulated categories** (health, finance, insurance, legal, housing, employment, credit, alcohol, gambling): check Google's policy for the category; some need certification or restrict targeting. Claims need proof on the page.

## After launch

- **Day 3**: conversions recording? Spend pacing? Ads approved?
- **Day 7**: first search-terms review. Add negatives for clear junk; add converting searches as keywords.
- **Weekly**: search terms (waste, winners, drift), budget pacing, conversion quality with the owner.
- **Day 30**: full audit (`google-ads-audit --blueprint`). Decide on bidding changes, budget shifts and phase 2.
