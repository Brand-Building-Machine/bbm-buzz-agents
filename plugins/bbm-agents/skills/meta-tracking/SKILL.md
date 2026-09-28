---
name: meta-tracking
description: Check that the owner's Meta (Facebook) lead tracking works, so the ad system learns from real leads. Covers instant-form lead delivery to the owner's inbox or CRM, the Meta pixel and Conversions API (CAPI) on the website, the Lead event, duplicate counting, match quality, and sending lead outcomes back from the CRM. Produces a plain-English fix list. Use when the owner says "are my leads tracking", "Meta shows leads I never got", "my form fills aren't showing in Ads Manager", "set up the pixel", "what is CAPI", before the first website lead campaign, or when meta-audit numbers look wrong. Read-only.
---

# meta-tracking

Meta optimizes toward whatever it is told a lead is. If that signal is missing, doubled or junk, every other skill is working blind. This skill finds out which, and writes the fixes. It never changes the website, the pixel or the CRM.

`scripts/meta.py` is in the **meta-audit** skill's folder (`python3` on macOS/Linux, `python` or `py` on Windows). Connector notes: `meta-audit/references/connector.md`.

## Start

1. `meta.py paths` and read `meta-ads.json`: `lead_method`, `pixel_id`, the website (from `brand-bible.md`).
2. Ask the owner three things: where do leads go today (email, CRM name, a spreadsheet), who calls them and how fast, and roughly how many leads last week they actually received (to compare with Ads Manager).

## Check 1: Leads arrive (instant forms)

- Ads Manager counts a form lead the moment it's submitted. Leads sit in Meta's **Leads Center** / Page leads until something moves them. **Meta deletes form leads after 90 days** unless they are downloaded or synced, so an unsynced form loses leads.
- Compare Ads Manager's lead count for last week with what the owner received. A gap means the sync is broken or missing.
- Fix options, simplest first: Meta's native integration with their CRM (many CRMs have one in Meta's partner list); Leads Center email notifications; a connector tool the owner already pays for. Recommend one, don't install anything.
- Test: the owner submits their own form using Meta's lead ads testing tool (search "Lead Ads Testing Tool" on Meta for Developers) and confirms it arrives where it should within minutes.

## Check 2: The website sends a Lead event (website leads)

With the connector: dataset tools (for example `ads_get_dataset_details`, `ads_get_dataset_quality`) show which events arrive, from where (browser pixel, server/CAPI or both), and their match quality. Without it: Events Manager → the dataset → Overview, or the owner screenshares.

Look for, and report plainly:
- **A `Lead` event exists** and fires on the thank-you page or the form's success, **not** on page view or button click. Firing on page view floods Meta with fake leads.
- **One lead = one event.** Compare Lead events with real submissions for the same days. Double counts usually mean the pixel and CAPI both send it without matching `event_id`s, or two tags fire (for example a plugin plus manual code).
- **Server events (Conversions API)** are also sent. Browser-only tracking misses a share of leads to ad blockers and privacy settings. Many website platforms (Shopify, WordPress plugins, Squarespace, Wix, GoHighLevel and others) have a built-in CAPI switch; that's the recommendation before any custom code.
- **Deduplication:** when pixel and CAPI both send a Lead, they must carry the **same event name and the same `event_id`**. Meta merges them; otherwise each lead counts twice.
- **Match quality:** Events Manager rates how well events match Meta accounts. For Lead, aim for "Good" or better. It improves by sending (hashed, by the platform) email and phone from the form, plus the `fbp`/`fbc` browser cookies and an external id. Don't promise a specific score.
- **Domain verified** in Business Settings, and the Lead event is the one the campaigns optimize for.

## Check 3: Outcomes flow back (later, when volume allows)

The strongest lead-quality lever on Meta: send CRM stages (qualified, booked, won) back through the Conversions API so Meta can optimize for leads that become customers ("conversion leads" for instant forms). Needs: leads synced into a CRM with the Meta lead id kept, and the CRM or an integration sending stage changes to Meta. Recommend it once the account gets roughly 20+ leads a week and the basics above pass. Before that, the owner's weekly "how many were real" count (meta-audit) is enough.

## Write it up

Save to `<reports folder>/YYYY-MM-DD-tracking-<business>.md`:

```
# Meta tracking check: <business> (<date>)
Verdict: <working / partly working / broken> | Lead method: <instant form / website>

## Fix first
1. <problem in plain words> | Evidence: <what you saw> | Fix: <exact step> | Who: <owner / web person / CRM admin> | Test: <how we'll know>

## What's working
## Not checked
<what you couldn't see: no Events Manager access, no CRM access, and so on>
```

## Report to the owner

A top-level message: the verdict, the top 3 fixes and who does each, the path, "from meta-tracking". If tracking is broken, say plainly that ad results can't be trusted until it's fixed, and hold off on budget increases.

## Limits

Read-only. Never edit website code, install tags, change Events Manager settings or connect integrations; write the steps and the owner or their web person does them. Never ask for or store passwords or access tokens. Work from what the owner tells you, the files they point to, and Meta's connector. Don't search email, drives, calendars or other connected apps to check their numbers unless they ask you to, and first confirm the account is theirs.
