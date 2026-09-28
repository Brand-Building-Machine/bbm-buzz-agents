# Building in bbm-buzz-agents — read this first

You are adding skills or agents to Brand Building Machine's **public client plugin**. Three business-owner clients (Anthony Langdon, Chris Ball, Shawn Syverson at Big Sky Benefit Solutions) run these from Buzz agents on **Claude Code and Codex**, on **Mac and Windows** (Shawn is Windows). Walt owns it and tests with the real clients.

Working checkout: `~/BBM/local/repos/bbm-buzz-agents`. Spec: `~/BBM/vault/bbm/state/bbm-buzz-agents-spec.md`. Client setup page: `https://go.brandbuildingmachine.com/buzz-agents/setup/` (source `~/BBM/apps/bbm-hub/buzz-agents/setup/index.html`).

## Ship policy (Walt, standing)

**Ship everything you build straight to `release`.** Build → test → `git pull --rebase` → push `main` → `git push origin main:release`. Don't wait for a "ship it". Clients update automatically; Walt tests live.

## What's here

```
.claude-plugin/marketplace.json     Claude Code AND Codex read this (tested)
.agents/plugins/marketplace.json    Codex-native catalog
plugins/bbm-agents/
  .claude-plugin/plugin.json  .codex-plugin/plugin.json    bump "version" in both + marketplace.json
  personas/      prebuilt Buzz agents (templated {{SLOTS}}), installed by install-agent
  skills/        one folder per skill
  agents/        Claude subagents (Claude runtime only)
  examples/      buzz-agents.config.example.json
```

Shipped: `install-agent`, `workspace-config`, `brand-bible`, `wiki-ingest`, `wiki-ask`, `wiki-audit`, `yt-intel`, `yt-ask`, `yt-search`, `yt-corpus`. Personas: chief-of-staff, agent-builder, research-lead, youtube-desk.

## Rules for every skill

1. **No client or Walt data, ever.** No names, IDs, paths, credentials, client facts. The repo is public. Grep before committing: `grep -rIil -E "waltclay|/Users/|10593685|bbm_vault|clickup" plugins` should only hit test guards.
2. **Owner paths come from config, never assumed.** Every skill reads `buzz-agents.config.json` (lookup order: `$BUZZ_AGENTS_CONFIG` → `~/.bbm-agents.json` pointer → search upward from cwd). Copy the `load_config` pattern from `skills/brand-bible/scripts/brand.py`. Current keys: `OWNER_NAME CHIEF_NAME WORKSPACE_ROOT WORKSPACE_MAP PROPOSED_PATH BRAND_PATH RAW_SOURCES_PATH RESEARCH_RUNS_PATH WIKI_PATH STATE_PATH SCOPE_STATE_PATTERN TASK_RULES BOUNDARIES_FILE`. **A new key** → add it to the table in `skills/workspace-config/SKILL.md` and to `examples/buzz-agents.config.example.json` in the same commit.
3. **Brand-aware skills read the brand folder** (`BRAND_PATH`, may contain `{business}`): `brand-bible.md`, `voice-agent.md`, `offers.md`, `root.css`. Never invent brand facts; if a file is missing, tell the owner to run `brand-bible`.
4. **Scripts: stdlib Python only**, invoked by path relative to the skill folder ("`scripts/x.py` relative to this skill's folder"). Tell the agent `python3` on Mac/Linux, `python`/`py` on Windows. No bash-only steps, no symlinks, no `open`/`sips`, force UTF-8 output. A paid API or extra install (Playwright, Firecrawl) must be optional or clearly gated with the owner's yes and their own key.
5. **Runtime-neutral instructions.** Don't depend on Claude-only tool names in skills. Subagents in `agents/` are Claude-only; a persona that needs them says `runtimes: [claude]`.
6. **Drafts, not actions.** Nothing sends, publishes, spends or deletes without the owner's explicit yes. Git: commit only files the skill wrote, and only if the workspace map allows; push only if it says so.
7. **Client-facing templates: no em dashes.** Complete beats long.
8. **Porting from Walt's own skills** (`~/BBM/.claude/skills/`): they assume Walt's vault layout, his accounts, and often the OLD layout (`active/`, `memory/`). Keep the method, drop the plumbing. Audit first, then rebuild lean — don't copy files over.

## Test before shipping (all of it)

- Offline tests per skill in `skills/<name>/tests/`, run **separately, from outside the skill dir**: `cd /tmp && python3 -m pytest <abs path>/tests -q -p no:cacheprovider`.
- `claude plugin validate plugins/bbm-agents` and `claude plugin validate .` must pass.
- **A live run:** make a scratch workspace + config in your scratchpad, then
  `BUZZ_AGENTS_CONFIG=<cfg> claude -p "<realistic owner request>" --plugin-dir <repo>/plugins/bbm-agents --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill" < /dev/null`
  and check the files it produced against the skill's own rules.
- Remove `__pycache__` before committing.

## After shipping

- If clients do anything differently, update the setup page (add the prompt they paste), then publish from `~/BBM/apps`: commit + push the page, `cd bbm-hub && ./deploy.sh --prod --yes`, `curl` the URL to confirm 200.
- Report to Walt: what shipped, what was tested, what's untested (Windows and Codex live runs usually are).

## Working alongside another instance

Another Claude session may be building in this repo at the same time. `git pull --rebase` before you start and before every push. Keep commits small and per-skill. The shared files that collide — `README.md` skills table, `workspace-config/SKILL.md`, `examples/*.json`, the three version fields — edit them in one small commit right before pushing. Version: bump the minor for a new skill, patch for fixes.
