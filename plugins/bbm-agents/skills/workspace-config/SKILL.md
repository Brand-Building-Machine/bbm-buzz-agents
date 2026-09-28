---
name: workspace-config
description: One-time setup that tells the prebuilt bbm-agents where the owner's workspace is — their name, their chief of staff's name, and the folders agents read from and write to. Writes buzz-agents.config.json into the owner's workspace repo. Use before the first install-agent run, or when the owner says "my folders changed", "set up my agent config", or install-agent reports unresolved placeholders.
---

# workspace-config

Finds the owner's workspace, proposes the values the agents need, and writes them once the owner confirms. Everything machine- or business-specific lives here — never in the plugin.

## What you produce

`buzz-agents.config.json` at the root of the owner's workspace repo, plus a one-line pointer at `~/.bbm-agents.json` (`{"config": "<absolute path to that file>"}`) so agents running from `~/.buzz` can find it.

| Key | Meaning | Required |
|---|---|---|
| `OWNER_NAME` | What agents call the owner (first name) | yes |
| `CHIEF_NAME` | Display name of their chief-of-staff agent (existing one if they have it) | yes |
| `WORKSPACE_ROOT` | Absolute path to the workspace repo checkout | yes |
| `WORKSPACE_MAP` | Absolute path to the file that explains the folder layout (AGENTS.md, CLAUDE.md, a MAP file) | yes |
| `PROPOSED_PATH` | Absolute path where agents put drafts the owner hasn't confirmed | yes |
| `RAW_SOURCES_PATH` | Absolute path where raw sources land before filing: meeting transcripts, YouTube Desk output, clippings (the wiki skills read it) | yes |
| `RESEARCH_RUNS_PATH` | Absolute path where Research Lead writes run folders | yes |
| `WIKI_PATH` | Absolute path to the wiki (`entities/`, `concepts/`, `topics/`, `index.md`, `log.md`). Existing one if the workspace has it; otherwise propose `<knowledge folder>/wiki` | yes |
| `STATE_PATH` | Absolute path to living state (`current/`, `decisions/`, `meetings/`) | yes |
| `SCOPE_STATE_PATTERN` | Only if the workspace tracks several businesses/clients separately: the per-scope state folder with `{scope}` in it, e.g. `/…/state/projects/{scope}` | no |
| `BRAND_PATH` | Absolute path to the brand folder (`brand-bible.md`, `voice-agent.md`, `offers.md`, `root.css`). If the owner runs several businesses, include `{business}`, e.g. `/…/canon/businesses/{business}/brand` | yes |
| `TASK_RULES` | One sentence on the task tool, e.g. "Create tasks in ClickUp list X; every task needs a due date; assignee id N." | no — leave empty if none |
| `BOUNDARIES_FILE` | Absolute path to the owner's written approval/autonomy rules, if they have one | no |

Example: `examples/buzz-agents.config.example.json` in the plugin root.

## Steps

1. **Find the real workspace — don't assume.** Check this channel's canvas, the instruction files loaded from the Buzz launch folder (`~/.buzz/AGENTS.md`, `~/.buzz/CLAUDE.md`), and the repos folder they name. Confirm the checkout by its git remote and its root instruction file. If two copies look plausible, list both and ask which one. Do not pull, switch branches or reset to orient yourself.

2. **Read the workspace's own map** (its AGENTS.md / CLAUDE.md / MAP). Use the folders it already defines. If it has a draft/proposed area, use it. If it has none, propose `<root>/proposed/` and say it's new. **Never reorganize the workspace to fit these agents.**

3. **Propose the whole file in one message** — every key, its value, and one line on where you found it. Recommend values; the owner corrects in one line. Ask only about what you truly couldn't find (usually `CHIEF_NAME` and `TASK_RULES`).

4. **After a yes**, write the file with absolute paths using the OS's native separators (Windows paths are fine; JSON needs `\\` escaped). Create any missing folders you proposed. Write the pointer file `~/.bbm-agents.json`.

5. **Verify:** run `python3 <install-agent skill dir>/scripts/agents.py config` (Windows: `python` / `py`) and confirm every path exists. Then `agents.py render chief-of-staff` must exit 0, and `python3 <wiki-ingest skill dir>/scripts/wiki.py paths` must resolve every knowledge path (run `wiki.py init` to create a missing wiki after telling the owner).

6. **Commit only the config file** to the workspace repo if the owner's workspace rules allow agents to commit; otherwise leave it for them and say so. Never commit anything else as part of this.

## Rules

- Absolute paths only. Agents run from `~/.buzz`, where relative paths resolve to nothing.
- One config per machine. If the owner runs agents on two machines, each gets its own pointer file; the config in the repo can hold only one set of absolute paths, so say which machine it's for.
- No secrets in the config. No API keys, tokens or passwords — ever.
