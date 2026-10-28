---
name: wiki-audit
description: "Check wiki links, unprocessed sources, stale claims and contradictions; report evidence-backed fixes without changing knowledge."
---

Resolve the workspace from `bbm-client.json` in the selected workspace or its parent directories; an explicit `BBM_CLIENT_CONFIG` path takes precedence. Run `python3 <wiki-ingest skill directory>/scripts/wiki.py paths` (Windows: `py` or `python`). Paths in config are relative to that config, never the plugin cache. Read the root AGENTS.md, workspace map and boundaries before working. If no config exists, use workspace-setup. Never fall back to another workspace or global agent configuration.

Run wiki.py lint --json for structural findings. It checks exact vault-relative links, orphan wiki pages, and old/un-dated unprocessed sources. Review relevant current state, decisions and recent source notes for contradictions, duplicates, missing topics and outdated claims. A script pass does not prove semantic correctness.

Read-only by default: give counts, the highest-impact supported issue and specific source paths. If a saved report is requested, create a unique dated file under WIKI_PATH/audits; do not overwrite an earlier report. Do not delete, rewrite canon or silently repair findings. Scope negative claims to the files inspected.

