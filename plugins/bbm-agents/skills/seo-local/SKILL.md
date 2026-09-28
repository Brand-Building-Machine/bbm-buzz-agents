---
name: seo-local
description: Local SEO for a business that serves customers in a place: Google Business Profile completeness, reviews, name/address/phone consistency across the site and listings, local schema, service and location pages, and citations (Apple, Bing, Yelp, BBB, industry directories). Produces a local score and a prioritized action list, plus ready-to-use fixes (schema, a review-request message, profile text) as drafts. Use when the owner asks about Google Maps, the map pack, Google Business Profile, "near me", reviews, service areas, listings, or "why don't I show up locally". Never edits a profile or listing itself.
---

# seo-local

For local businesses, the map pack and local results are most of the win. This skill checks what the owner controls: their Google Business Profile, their reviews, their website's local signals, and their listings.

Uses `seo.py` from the `seo-audit` skill (the folder next to this one): `python3 <seo-audit skill dir>/scripts/seo.py` (Windows: `python` / `py`). `seo.py paths` shows where reports go. Details for the profile questionnaire and citations: `references/local-method.md` in this skill's folder.

## What actually moves local rankings

In order of weight (expert surveys and correlation studies; use as an order, never as exact percentages):

1. **Primary Google Business Profile category**: the most specific true one ("Employee Benefits Consultant" beats "Insurance Agency" if that's what they are). A wrong primary category is the worst self-inflicted problem.
2. **Proximity** to the searcher. The owner can't change it. Say so, so they stop worrying about it and focus on the rest.
3. **Reviews**: count, rating, and recency. Velocity beats volume.
4. **A dedicated website page for each core service.** The biggest content lever for most small service businesses.
5. Additional categories, profile completeness, name/address/phone consistency, links from local sites.

Myths to correct if they come up: geotagging photos does nothing; profile posts don't directly raise rankings; attributes are filters, not ranking factors; stuffing keywords into the business name breaks Google's rules and risks suspension.

## Flow

**1. Business type.** From the brand folder and the site: **storefront** (customers come to them), **service-area business** (they go to customers, address hidden), or **hybrid**. For service-area businesses, Google ranks from the verification address; the service area list doesn't change rankings. Skip map-embed and street-address checks for them.

**2. Industry.** Pick one for weighting: `professional` (brokers, accountants, agencies), `legal`, `healthcare`, `home_services`, `restaurant`, `real_estate`, `automotive`, or `general`. YMYL industries (insurance, benefits, health, finance, legal) need licence numbers and credentials visible.

**3. Google Business Profile.** No API: ask the owner to open their profile (or paste its public URL, or a screenshot) and go through the 25 fields in `references/local-method.md` in one message with your best guess for each from what you can see. Score each 0 (missing), 1 (present), 2 (present and good), or `"na"`. Save the answers as JSON in the reports folder and run:
`seo.py gbp <answers.json> --industry <industry>`
Unanswered fields are left out of the score and listed, never guessed.

**4. Name, address, phone.** Get the exact name, address and phone from the profile (the owner confirms). Then:
`seo.py nap <homepage> <contact page> <footer-bearing service page> --name "..." --address "street, city, state zip" --phone "..."`
Severity: name mismatch Critical, address mismatch High, phone mismatch Medium. Also flags dead `*.business.site` links and "message us on Google" CTAs (both shut down by Google in 2024).

**5. On-site local signals.** `seo.py page <url>` on the homepage and each core service page. Check: city and service in title and H1; name, address, phone in text (not only in an image); a `tel:` link; LocalBusiness schema of the most specific type with address, phone, hours, `geo` to 5 decimal places, and `sameAs` links to the profile and listings; one page per core service; a map embed for storefronts (reinforcement only, not a ranking factor).

**6. Reviews.** Ask for: current Google review count, count about 90 days ago (or date of the last review), average rating, and share of reviews with an owner reply. Heuristic targets (practitioner observations, not Google rules): get to 10 reviews first; then a new review at least every 2-3 weeks; reply to 80%+; many buyers filter at 4.0+ stars.

**7. Citations.** The listings in `references/local-method.md`: Tier 1 everywhere, plus the industry's directories. With a web search tool, search `"<business name>" <city>` per site and fetch the listing; otherwise ask the owner for their listing links. Compare name, address and phone on each. Apple Business Connect and Bing Places are free, often unclaimed, and feed Apple Maps, Siri, Bing and assistants that use Bing's data.

**8. Location pages** (multi-location or city pages only): each must pass the swap test (swap the city name and it no longer makes sense). Real local content: team there, local jobs or clients, local reviews, local FAQs. Warn above 30 city pages; above 50 needs a real reason.

## Local score

| Dimension | Weight | Full marks look like |
|---|---|---|
| Google Business Profile | 25 | `gbp` score 90+ |
| Reviews | 20 | 10+ reviews, 4.5+ stars, one in the last 3 weeks, replies to most |
| Local on-page | 20 | service + city in titles/H1s, NAP in text, tel link, a page per core service |
| NAP and citations | 15 | no mismatches; Tier 1 listings claimed and matching |
| Local schema | 10 | specific type, full address, phone, hours, geo, sameAs, valid |
| Local links | 10 | chamber, associations, local press, sponsorships visible |

Score each dimension Full / Partial / Low from what you actually saw. Unmeasured → "not measured", not a guess.

## Drafts you can produce (owner approves every one)

- **LocalBusiness schema** block filled from the brand folder and the confirmed NAP. Unknown fields left out.
- **Profile description** (up to 750 characters; aim 250-750): what they do, for whom, where, in their voice. No keyword stuffing, no URLs, no promo prices.
- **Review-request message** (text/email) in their voice. **Never gate reviews**: don't ask "happy? leave a review; not happy? email us." Google's policy and the FTC's rule on consumer reviews both prohibit it, with real penalties. Ask everyone the same way.
- **Review replies**: short, specific, thankful. Never confirm someone is a patient or client in a regulated field (health, benefits, legal), never share plan or case details.
- **Service page briefs** for missing core services: hand off to `seo-page`.

## Report

Save `<reports folder>/YYYY-MM-DD-local-<business>.md`: local score + dimension table; business type and industry; profile checklist result; review snapshot; NAP table; citations status; schema status with the ready-to-paste block; **top 10 actions** in order with who does each; and a "not checked" line (live map rankings, profile insights, backlinks, anything the owner didn't answer).

Quick wins to look for first: wrong or generic primary category; unclaimed Apple Business Connect or Bing Places; NAP mismatches; missing LocalBusiness schema; no `tel:` link; no page for a core service.

Checking live rankings needs a paid rank tracker. Without one, the owner can search their main service from 3-5 spots in their area (or ask customers what they see) and you record it as a snapshot, clearly labelled as such.

## Rules

- Never edit the Google Business Profile, listings, or the site. Draft the change; the owner applies it.
- Never write fake reviews, review replies posing as customers, or listings for addresses the business doesn't operate from.
- Never invent a review count, rating, licence number or competitor fact. Ask.
- No em dashes in anything the owner will publish.

Method adapted from claude-seo by AgriciDaniel (MIT). See `CREDITS.md` in the plugin root.
