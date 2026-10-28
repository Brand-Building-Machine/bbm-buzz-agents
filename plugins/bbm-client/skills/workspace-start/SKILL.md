---
name: workspace-start
description: "Orient the owner in their configured workspace and identify the next useful step from recorded priorities."
---

Resolve the workspace from `bbm-client.json` in the selected workspace or its parent directories; an explicit `BBM_CLIENT_CONFIG` path takes precedence. Run `python3 <wiki-ingest skill directory>/scripts/wiki.py paths` (Windows: `py` or `python`). Paths in config are relative to that config, never the plugin cache. Read the root AGENTS.md, workspace map and boundaries before working. If no config exists, use workspace-setup. Never fall back to another workspace or global agent configuration.

Read the relevant canon, current state and knowledge index. Lead with what is recorded, the next useful action and any missing evidence. Cite paths and dates. Stay within the selected business. Suggest useful follow-ups; do not turn suggestions into commitments. This is read-only.

