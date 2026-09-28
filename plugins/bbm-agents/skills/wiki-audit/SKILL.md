---
name: wiki-audit
description: Health check of the owner's knowledge base. Structural checks (orphan pages, sources never filed, broken references, dead links) run by script; semantic checks (contradictions, stale claims, duplicate pages, missing topics, insights that should be promoted) are read and judged. Produces a dated report with a suggested fix per finding. Read-only — never fixes anything itself. Use for "audit the wiki", "health check my knowledge base", "what's stale", "any contradictions", "anything duplicated".
---

# wiki-audit

Surfaces the rot that builds up as a knowledge base grows. **Read-only: it writes one report and changes nothing else.** The owner decides what to fix (usually by asking for it next).

Folder locations and the structural checks come from `python3 <wiki-ingest skill dir>/scripts/wiki.py` (Windows: `python` / `py`). The wiki-ingest skill folder sits next to this one.

## Options

- `--structural` — script checks only. Near-free.
- `--window <days>` — how far back to read meetings/sessions for the semantic checks (default 45).
- `--scope <name>` — one business/client/project only.

## 1. Structural (script)

`wiki.py lint` (add `--json` if you want to post-process). Four checks:
1. **Orphans** — wiki pages nothing links to (the index counts as a link).
2. **Stale sources** — raw sources still `unprocessed` after 7 days (`--stale-days N`).
3. **Broken `related:`** — references to ids that don't exist.
4. **Dead wikilinks** — `[[Links]]` with no matching page.

Sanity-check a sample before reporting — a link to a page with a slightly different name is a real finding; a false positive from an unusual file is not. For each, suggest the fix (link it from a related page, run wiki-ingest, correct the id, repoint to the closest page).

## 2. Semantic (read and judge)

Group related files first: curated pages (wiki pages, `decisions/`, `current/`) plus meetings/sessions inside the window that share links, tags or repeated names. Read each group before judging. **Emit a finding only when your reasoning confirms it**, with one or two sentences of reasoning specific to that case. A finding without reasoning is noise.

5. **Contradictions** — two sources both claiming to be current, disagreeing about the same thing, no supersession. Not a contradiction if one clearly replaced the other (→ check 6) or they're about different times/scopes. Fix: name the likely winner.
6. **Stale claims** — a curated page says X; a newer meeting/decision says it changed. Fix: the rewrite, citing the newer source.
7. **Duplicates** — two or more pages covering the same thing. Fix: which page is canonical, what to fold in, where to redirect links. Never delete — archive.
8. **Missing topics** — three or more recent meetings/notes circling a theme with no page. Fix: the page to create and its one-line definition.
9. **Promotions** — a durable decision, rule or insight stuck in a meeting note or the log that belongs in `decisions/`, `current-strategy.md` (Standing rules) or a wiki page. Fix: the destination.

## Report

Write `WIKI_PATH/audits/YYYY-MM-DD-audit.md`:

```markdown
---
title: "Knowledge Audit — YYYY-MM-DD"
type: audit
date: YYYY-MM-DD
---

# Knowledge Audit — YYYY-MM-DD
Window: N days · Scope: {scope or "whole workspace"}

## Summary
Orphans N · Stale sources N · Broken refs N · Dead links N · Contradictions N · Stale claims N · Duplicates N · Missing topics N · Promotions N

## Structural
### Orphans (N)
- `path` — Fix: …
(… one section per check, then Semantic, each finding with Reasoning + Fix)
```

Append to `log.md`:
```
## [YYYY-MM-DD] audit | Knowledge health check
Report: audits/YYYY-MM-DD-audit.md
```

Commit only the report and the log line, and only if the workspace lets agents commit. Don't push unless the workspace rules say agents push.

## Tell the owner

The counts, the **one** most urgent item, and the report path. Offer to fix the top few — each fix is a separate, approved change.
