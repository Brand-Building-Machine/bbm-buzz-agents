# BBM Client

Portable knowledge workflows for Claude Code and Codex.

# Install and update shared skills

The marketplace repository has a legacy name. Install only `bbm-client`; the separate `bbm-agents` plugin is for messaging-platform agents and is not required.

Claude Code:
```
claude plugin marketplace add "Brand-Building-Machine/bbm-buzz-agents#release"
claude plugin install bbm-client@bbm-buzz-agents
```
Codex:
```
codex plugin marketplace add Brand-Building-Machine/bbm-buzz-agents --ref release
codex plugin add bbm-client@bbm-buzz-agents
```
Restart the assistant after installation. Verify it lists bbm-client and can find workspace-start and wiki-ingest. These commands install skills, not account access.

Claude updates: `claude plugin marketplace update bbm-buzz-agents`, then `claude plugin update bbm-client@bbm-buzz-agents`.
Codex updates: `codex plugin marketplace upgrade`, then restart and verify the plugin version. Use the installed CLI's help if its options differ.

Do not edit plugin-cache files. Keep custom skills in your workspace with distinct names. Existing users of bbm-agents should choose one provider for overlapping wiki skills in each workspace; no automatic migration or removal is performed.

Standalone pack: a maintainer can run `scripts/export-client-pack.py /chosen/new-pack.zip` in the distribution repo. The zip contains the same reviewed skills and a README. Extract selected skills into `.agents/skills/` (Codex) or `.claude/skills/` (Claude) only after inspecting existing names. Never overwrite custom skills; review updates as diffs. Plugin installation is the recommended update path.

Includes workspace-setup, workspace-start, source-capture, wiki-ingest, wiki-ask, wiki-audit and save-session. No personas, agent installer, connectors or background capture. Python 3.10+; stdlib only.
