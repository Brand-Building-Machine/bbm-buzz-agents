---
name: wiki-ask
description: Answer a question from the owner's knowledge base — what we know, what we decided, what's happening with a business or client — with citations to the pages it came from. Offers to save substantial answers back as a wiki page. Use for "what do we know about X", "what did we decide about Y", "catch me up on Z", "summarize what's happened with <client/project>". Skip for one-fact lookups a single file read answers.
---

# wiki-ask

Answers from what's recorded, not from memory or general knowledge. If it isn't recorded, say so.

Folder locations come from the owner's config: run `python3 <wiki-ingest skill dir>/scripts/wiki.py paths` (Windows: `python` / `py`). The wiki-ingest skill folder sits next to this one.

## Steps

1. **Start at the right map.**
   - About one business / client / project → its state folder (`<scope>/current/`, `decisions/`, `meetings/`) plus the wiki index.
   - Cross-cutting, or unclear → `index.md` in `WIKI_PATH` first.
   - Also read the workspace map (`WORKSPACE_MAP`) if you don't know where something lives.
2. **Read the candidate pages.** Follow `[[wikilinks]]` and `related:` one hop when they're clearly relevant. For "what did we decide", read `decisions/` — including `status: superseded` ones only to explain history.
3. **Answer.** Lead with the answer. Cite every claim with the page it came from (`[[Page]]` or the file path). Keep it short unless the owner asked for depth.
4. **Say what's missing or conflicting.**
   - Nothing found: say so plainly, and offer to capture it ("want me to add a source for this?").
   - Two pages disagree: show both with dates; the newer authoritative one usually wins — say which you'd trust and why.
   - The answer depends on a page that hasn't been updated in a long time: say how old it is.
5. **Offer to save it.** If the answer is substantial (pulls several sources together or frames something new), ask once: "Save this as a wiki page?" On yes → `WIKI_PATH/topics/{Name}.md` (or `concepts/`), with `sources:` listing the cited pages. Add it to `index.md`.
6. **Log it** — append to `log.md`:
   ```
   ## [YYYY-MM-DD] query | "{short question}"
   Read: [[Page A]], [[Page B]]
   Saved as: [[New Page]] | not saved
   ```

## Never

Answer from general knowledge when the owner asked what *we* know. Present an old page as current without saying its date.
