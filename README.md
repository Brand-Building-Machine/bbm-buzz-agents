# BBM Buzz Agents

Prebuilt [Buzz](https://github.com/block/buzz) agents and the skills they run, from Brand Building Machine.
One plugin, installed once, used by both **Claude Code** and **OpenAI Codex** agents. Updates arrive on their own.

| Agent | What it owns | Runtime |
|---|---|---|
| **Chief of staff** | Gets things done for the owner and keeps them on point | Claude or Codex |
| **Agent Builder** | Installs prebuilt agents; designs new ones only when nothing fits | Claude |
| **Research Lead** | Commissioned research with a four-subagent team, sourced and fact-checked | Claude |
| **YouTube Desk** | Briefs, answers and searches from YouTube | Claude or Codex |

**Nothing on your machine writes these personas.** They're finished. Installing one fills in your name and
folder paths, then opens a draft in Buzz Desktop that **you** approve. It isn't an agent until you save it.

## Install (once per machine)

Paste [`SETUP_PROMPT.md`](SETUP_PROMPT.md) to your chief of staff in Buzz, or to Claude Code. It does all of this:

**Claude Code** — add to `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`), merging with what's there:

```json
{
  "extraKnownMarketplaces": {
    "bbm-buzz-agents": {
      "source": { "source": "github", "repo": "Brand-Building-Machine/bbm-buzz-agents", "ref": "release" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "bbm-agents@bbm-buzz-agents": true }
}
```

**Codex:**

```
codex plugin marketplace add Brand-Building-Machine/bbm-buzz-agents --ref release
codex plugin add bbm-agents@bbm-buzz-agents
```

Then restart Buzz so agents start fresh sessions.

## Use

In any Buzz channel, to your chief of staff or Agent Builder:

- "Set up my agent config" → `workspace-config` (once)
- "What agents can I install?" → `install-agent`
- "Install YouTube Desk" → opens a draft you approve
- "Are my agents up to date?" → offers updates as drafts

## Updates

Clients track the `release` branch. Claude Code pulls it automatically (loads next session). Codex refreshes git
marketplaces at startup; to force it: `codex plugin marketplace upgrade`. Persona updates never apply
themselves — `install-agent` offers them as drafts for you to approve.

## What's inside

```
plugins/bbm-agents/
  personas/     the four agents (templates with {{PLACEHOLDERS}})
  skills/       install-agent, workspace-config, yt-intel, yt-ask, yt-search, yt-corpus
  agents/       Claude subagents for Research Lead: youtube-scout, web-scout, trend-analyst, fact-checker
  examples/     sample config
```

No client data, credentials or machine paths live in this repo. Yours stay in your own workspace.

## Requirements

Python 3.10+ and `yt-dlp` for the YouTube skills. A Gemini API key is optional (videos without captions,
bulk corpus extraction) and must be your own.

MIT licensed.
