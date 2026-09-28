---
name: wiki-ingest
description: File a raw source (meeting transcript, clipping, YouTube brief, note) into the owner's knowledge base. Creates or updates wiki pages for the people, companies, tools and ideas in it, keeps the index and log current, and — for meetings — files a curated meeting note and rolls the meeting forward into living state (next actions, risks, strategy) and decisions. Use when the owner says "ingest this", "file this meeting", "process the new transcript", "add this to the wiki/knowledge base", or when unprocessed sources are waiting.
---

# wiki-ingest

Turns raw sources into durable, findable knowledge. Pattern: read the source → update the wiki pages it touches → file the meeting and roll it forward → update index and log → mark the source processed.

The script is `scripts/wiki.py`, relative to this skill's folder (the folder containing this SKILL.md). Run it with `python3` on macOS/Linux, `python` or `py` on Windows.

## Where things live — from the owner's config, never assumed

Run `wiki.py paths` first. It resolves, from the `buzz-agents.config.json` that `workspace-config` wrote:

| Key | What it is |
|---|---|
| `RAW_SOURCES_PATH` | Raw sources waiting to be filed (`status: unprocessed` in frontmatter) |
| `WIKI_PATH` | The wiki: `entities/`, `concepts/`, `topics/`, plus `index.md` and `log.md` |
| `STATE_PATH` | Living state: `current/`, `decisions/`, `meetings/` |
| `SCOPE_STATE_PATTERN` | Optional. When the workspace tracks several businesses or clients separately, the per-scope state folder, e.g. `.../state/projects/{scope}` |

If a key is missing, stop and run `workspace-config`. If the wiki folders don't exist yet, tell the owner in one line and run `wiki.py init` (it creates only what's missing and never overwrites). **Also read the workspace map (`WORKSPACE_MAP` in the config) — where the workspace already has its own convention for something, follow it over this file.**

## Invocation

- **One source:** "ingest <file>" → process exactly that file.
- **Everything waiting:** `wiki.py unprocessed` lists them oldest first. **Process one source at a time** — finish all steps for one before opening the next. The roll-forward in step 4 is the expensive part, and it's the part that silently gets skipped when many sources share one context. More than ~3 waiting? Do them one per turn and say so.

## Steps

**1. Read the source** — frontmatter and body.

**2. Identify wiki targets.**
- **Entities** — people, companies, products, tools → `WIKI_PATH/entities/{Display Name}.md`
- **Concepts** — methods, frameworks, patterns → `WIKI_PATH/concepts/{Display Name}.md`
- **Topics** — themes that cut across several entities/concepts → `WIKI_PATH/topics/{Display Name}.md`

Only what the source actually says something durable about. A passing mention is not a page.

**3. Create or update each page.**
- New page frontmatter: `title`, `type` (entity|concept|topic), `sources: [<source id or filename>]`, `related: []`, `tags: []`, `last_updated: YYYY-MM-DD`. Body: a one-line definition, then what we know, with `[[wikilinks]]` to related pages.
- Existing page: add the new information where it belongs (not appended at the bottom as a dated block), append the source to `sources`, refresh `last_updated`. If the new source contradicts the page, say so on the page with both sources linked — don't silently overwrite.

**4. Meetings only — file it, then roll it forward. Do not skip the roll-forward.**

Decide the scope: which business/client/project the meeting is about. With `SCOPE_STATE_PATTERN`, that's the per-scope folder; otherwise `STATE_PATH`. A meeting that covers two scopes files into both. Can't tell? Park it (see below).

*a. Curated meeting note* → `<scope>/meetings/YYYY-MM-DD-{slug}.md`. **Dedup first:** if a note for the same date and meeting exists, merge anything new into it and add a line pointing at the raw source — don't create a second file. The raw transcript stays in `RAW_SOURCES_PATH`; the meeting note is the curated version (who, what was discussed, decisions, next steps with owners and dates).

*b. Roll forward into living state* — `<scope>/current/`. These files are overwritten state, not logs. Re-read each one first; touch it only if the meeting changed it. If the workspace already has its own `current/` files, use those names; otherwise these three:

- `next-actions.md` — add action items the meeting created (owner + date); check off or remove the ones it resolved. A live to-do list, not a history.
- `bugs-and-risks.md` — **exactly two sections**, ≤800 tokens:
  - `## Live risks` — could hurt AND nobody is fixing it
  - `## Watching` — might become a risk
  Test before writing: has an owner and a deadline → it's a task (next-actions). A choice that was made → it's a decision. Resolved → delete it; the meeting note is the record. Never keep a "Resolved" section.
- `current-strategy.md` — ≤1,500 tokens, fixed sections: `## The bet` · `## Working` · `## Testing` · `## Next` · `## Standing rules`. **No dated section headings, ever.** When direction changes, overwrite the affected bullet. Permanent constraints ("never do X", "always check Y") go in Standing rules — the most valuable section.

*c. Decisions* — `<scope>/decisions/YYYY-MM-DD-{slug}.md`, **only for a genuine decision**: a choice that closes off alternatives and has lasting consequences. Most meetings produce zero. When in doubt, it's a next-action. Decisions are never edited after the fact: to reverse one, write a new decision with `supersedes: [<old id>]` and set the old one's `status: superseded`. Reflect the resulting direction in `current-strategy.md`.

*d. Standing goals are a review gate.* If a decision would change a standing goal or target the workspace keeps (a KPI floor, budget, quarterly objective — wherever the workspace map says goals live), **do not edit the goal file.** Write the decision as normal, and put the proposed goal change in `PROPOSED_PATH` for the owner to approve. A one-off result ("revenue was X this week") is never a goal change.

Filed a meeting note but touched no state file? Re-read the meeting — you probably skipped a real action item, risk or decision.

**5. Update `index.md`** — add new pages under Entities / Concepts / Topics, and add this source under Recent sources.

**6. Append to `log.md`:**
```
## [YYYY-MM-DD] ingest | {short description}
Source: {filename}
New: [[Page A]], [[Page B]]
Updated: [[Page C]]
State: {scope}: next-actions, current-strategy | none
```

**7. Mark the source** — frontmatter `status: unprocessed` → `status: processed`.

**8. Commit, if the workspace allows agents to commit** (check the workspace map). `git add` only the files this ingest wrote — never `git add -A`; other agents write here too. Commit message `Ingest: {short description}`. Push only if the workspace rules say agents push.

## Ambiguity — park it, don't guess

Can't tell which scope a source belongs to, whether something is a real decision, or where it goes? File everything you're confident about, leave the source `status: needs-review`, add `review_question: "<the specific question>"` to its frontmatter, and ask the owner that one question. Never mark a source processed that you only half-filed.

## Report to the owner

A few lines: what was filed where, pages created/updated, state files touched, decisions written, anything parked and the question. Name paths; don't paste the pages.

## Never

- Invent facts, attendees, numbers or decisions the source doesn't contain.
- Put secrets (keys, passwords, account numbers) from a transcript into the wiki. Note that a secret was shared and where, never the value.
- Reorganize the workspace's folders to match this skill.
