---
name: meta-launch
description: Build or change the owner's Facebook and Instagram lead ads safely. Turns approved concepts or audit recommendations into a written change plan (campaign structure, budget, targeting, ads, form), checks it against Meta's rules and the owner's own limits, and only after the owner approves that exact plan applies it through Meta's ads connector, everything created PAUSED and read back to confirm. Turning ads on is a separate approval. Use when the owner says "launch these ads", "set up a Facebook lead campaign", "change my budget", "pause that ad", "turn the ads on", or after meta-creative or meta-audit.
---

# meta-launch

Every change to a Meta ad account can spend money or stop leads. This skill separates **plan → approve → apply → confirm**, and never skips a step. It never deletes anything.

`scripts/meta.py` is in the **meta-audit** skill's folder (`python3` on macOS/Linux, `python` or `py` on Windows). Meta's connector: `meta-audit/references/connector.md`. Build rules and API gotchas: `references/build-rules.md` (read it before your first plan in a session).

## Before you start

1. `meta.py profile check [--business <name>]` must pass. It needs: ad account, Facebook Page, lead method, what a qualified lead means, target cost per qualified lead, **max daily budget**, special ad category and countries. Missing → fill it in with the owner (meta-audit, "Set the target"). **No max daily budget = no plans that spend.** Absent a ceiling, nothing is written.
2. **Confirm the account.** Read it from the connector and say it back by name and id: "This is <name> (act_…)?" Wait for yes, every session, even if there is only one account.
3. Website leads → the pixel must be firing a Lead event. If unsure, run `meta-tracking` first.

## 1. Decide the shape (lead gen, small budget)

From `references/build-rules.md` §1, stated plainly to the owner:
- **One campaign, one ad set, broad targeting** (country or service area, Advantage+ audience on), 3-6 ads. Most small budgets can't feed more. `meta.py tcpl ... --daily-budget N` says how many ads the budget feeds.
- Add a separate testing campaign (about 20% of budget, winners stay in the main one) only when the ad ceiling is 8+.
- Objective **Leads** (`OUTCOME_LEADS`). Instant form or website per the profile.
- Special ad category declared if it applies. It limits targeting; say so.

## 2. Write the plan

Read current state from the connector first (never plan from memory). Write the plan as JSON in `<reports folder>/plans/YYYY-MM-DD-<slug>.json`. Shapes and a full example: `references/build-rules.md` §3. Actions:

| Action | Use for | Notes |
|---|---|---|
| `create` | New campaign / ad set / ads | Always PAUSED |
| `update` | Budget, targeting, names, schedule | Every change carries `before` (read from the connector) and `after` |
| `pause` | Stop specific ads, ad sets or campaigns | Name the replacement if pausing a working ad |
| `activate` | Turn on specific paused objects | Always its own plan and its own approval. Starts spending |

Every plan has `title`, `reason`, `measure` (how we'll know it worked, with a date) and `undo`.

## 3. Check it

```
meta.py plan <plan.json> [--business <name>]
```

Exit 1 = **blocked**. Fix every block (or ask the owner the question the block names) and re-run. The output is the proposal: what it does to money and delivery, before → after, how to undo, heads-ups, and a **plan id** (a fingerprint of the exact content). Save it next to the JSON as `<same name>.md`.

## 4. Get approval

Post the proposal to the owner: the plan id, one line on what it does, the money line ("up to $30 a day once turned on"), and the heads-ups. Ask them to reply **"approve <plan id>"**.

- Only an explicit yes to **this plan id** counts. "Sounds good" to a different message, silence, or "go ahead with whatever" does not.
- Any change after approval, however small, is a new plan and a new id. Re-check, re-ask.
- The owner's connector should also be set to ask before write tools run; that is a second lock, not a replacement for this one.

## 5. Apply it

Only the approved plan, in order, one call at a time:
1. `create`: campaign (status PAUSED) → ad set (PAUSED) → creatives/ads (PAUSED). Pass `status: PAUSED` explicitly every time, even where it's the default. Budgets are sent in **cents** (the proposal shows the number).
2. `update` / `pause` / `activate`: exactly the listed targets and fields.
3. **Stop at the first error.** Do not change the objective, optimization goal, budget or targeting to get around an error. Explain the error to the owner in plain words with the options (`references/build-rules.md` §4) and write a new plan.
4. **A timeout or unclear response is not a failure you can retry.** Read the account to see what actually happened before doing anything else.
5. If the connector can't do a step (no image upload tool, account not enabled), stop there. Give the owner the plan and the proposal; everything in it can be built by hand in Ads Manager, paused, in a few minutes. Say which steps are done and which are theirs.

## 6. Confirm and log

Read every created or changed object back from the connector and compare it with the plan: status, budget, objective, optimization goal, targeting, destination, ad text. Then:

```
meta.py log <plan.json> --result verified|failed|unknown --ids "campaign=… adset=… ads=…" [--note "…"]
```

`verified` only when the read-back matches. Anything else is `failed` or `unknown`, with the reason in the note.

## Report to the owner

A top-level message: the plan id and title, the result (verified / failed / unknown), what now exists or changed (with names, never just ids), **that everything new is paused**, and the one next step ("reply 'approve <activate plan id>' when the images are in and you're ready to spend"). Path to the plan and log. "from meta-launch".

## Never

- Delete or archive anything. Offer pause instead.
- Turn anything on inside a `create` or `update` plan.
- Spend above `max_daily_budget`, or raise a budget more than 20% in one step without saying it will likely restart learning.
- Edit the creative of a running ad (it restarts learning). Launch a new ad beside it.
- Change an ad set's objective or optimization goal. That needs a new campaign.
- Retry a write blindly, or act on an approval for a different plan id.
