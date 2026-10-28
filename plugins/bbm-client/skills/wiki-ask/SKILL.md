---
name: wiki-ask
description: "Answer what is known or decided from the client vault, citing recorded evidence and its dates."
---

Resolve the workspace from `bbm-client.json` in the selected workspace or its parent directories; an explicit `BBM_CLIENT_CONFIG` path takes precedence. Run `python3 <wiki-ingest skill directory>/scripts/wiki.py paths` (Windows: `py` or `python`). Paths in config are relative to that config, never the plugin cache. Read the root AGENTS.md, workspace map and boundaries before working. If no config exists, use workspace-setup. Never fall back to another workspace or global agent configuration.

Read the knowledge index and relevant scope canon, current state and decisions. Follow relevant links one hop. Answer briefly with source paths and event dates, distinguishing fact, reported claim and interpretation. Say when something is absent or stale; never fill gaps with guesses. Report contradictions with both sources. This is read-only; save a synthesis only when requested.
