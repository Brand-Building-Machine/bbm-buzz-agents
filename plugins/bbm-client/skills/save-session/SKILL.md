---
name: save-session
description: "Capture decisions, progress and unresolved next steps from the current conversation in the client workspace."
---

Resolve the workspace from `bbm-client.json` in the selected workspace or its parent directories; an explicit `BBM_CLIENT_CONFIG` path takes precedence. Run `python3 <wiki-ingest skill directory>/scripts/wiki.py paths` (Windows: `py` or `python`). Paths in config are relative to that config, never the plugin cache. Read the root AGENTS.md, workspace map and boundaries before working. If no config exists, use workspace-setup. Never fall back to another workspace or global agent configuration.

Save a concise dated session note in the existing scope state/sessions. Record what happened, what was verified, decisions actually made, next steps and unresolved issues. Distinguish completion from intentions. Cite artifacts and user decisions; do not manufacture dates or owners. Reconcile routine current-state notes under the freshness policy. Propose standing-rule changes for approval. Report the path. Do not commit, push or send anything as part of saving a session.
