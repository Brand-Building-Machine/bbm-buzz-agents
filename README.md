# BBM Buzz Agents

Prebuilt [Buzz](https://github.com/block/buzz) agents and the skills they run, from Brand Building Machine.
One plugin, installed once, used by both **Claude Code** and **OpenAI Codex** agents. Updates arrive on their own.

| Agent | What it owns | Runtime |
|---|---|---|
| **Chief of staff** | Gets things done for the owner and keeps them on point | Claude or Codex |
| **Agent Builder** | Installs prebuilt agents; designs new ones only when nothing fits | Claude |
| **Research Lead** | Commissioned research with a four-subagent team, sourced and fact-checked | Claude |
| **YouTube Desk** | Briefs, answers and searches from YouTube | Claude or Codex |
| **SEO Desk** | Gets you found on Google, Maps and AI answers: audits, local SEO, pages and blog posts in your voice | Claude or Codex |

**Skills they use** (also usable directly):

| Skill | What it does |
|---|---|
| `brand-bible` | Builds your brand bible through a short interview: company, offers, customers, voice, colours and fonts. Everything else reads it |
| `wiki-ingest` | Files a meeting transcript or source into your knowledge base: wiki pages, meeting note, next actions, risks, strategy, decisions |
| `wiki-ask` | Answers "what do we know / what did we decide" from your knowledge base, with citations |
| `wiki-audit` | Health check: orphan pages, unfiled sources, dead links, contradictions, stale claims. Read-only |
| `yt-intel` · `yt-ask` · `yt-search` · `yt-corpus` | YouTube briefs, answers, search, and bulk transcripts |
| `seo-audit` | Audits your site: indexing, robots.txt, sitemap, broken links, titles, schema, images, speed, content quality. Scored, prioritized fixes |
| `seo-local` | Google Business Profile, reviews, name/address/phone consistency, local schema, listings |
| `seo-ai-search` | Whether ChatGPT, Perplexity, Claude and Google AI can find and quote you, and what to fix |
| `seo-page` | Writes or fixes a page to rank for a keyword, after checking what Google already ranks |
| `seo-blog` | Plans topics and a calendar, writes sourced, fact-checked posts, refreshes posts losing traffic |
| `install-agent` · `workspace-config` | Install/update the agents; one-time folder setup |

**Nothing on your machine writes these personas.** They're finished. Installing one fills in your name and
folder paths, then opens a draft in Buzz Desktop that **you** approve. It isn't an agent until you save it.

## Install (once per machine)

Paste [`SETUP_PROMPT.md`](SETUP_PROMPT.md) to your chief of staff in Buzz, or to Claude Code. It does all of this:

**Claude Code:**

```
claude plugin marketplace add "Brand-Building-Machine/bbm-buzz-agents#release"
claude plugin install bbm-agents@bbm-buzz-agents
```

Then turn on auto-update: in `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`), add
`"autoUpdate": true` to `extraKnownMarketplaces.bbm-buzz-agents`. Do this *after* the `add` command, which rewrites that entry.

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
- "Install SEO Desk" → same
- "Are my agents up to date?" → offers updates as drafts

## Updates

Clients track the `release` branch. Claude Code pulls it automatically (loads next session). Codex refreshes git
marketplaces at startup; to force it: `codex plugin marketplace upgrade`. Persona updates never apply
themselves — `install-agent` offers them as drafts for you to approve.

## What's inside

```
plugins/bbm-agents/
  personas/     the five agents (templates with {{PLACEHOLDERS}})
  skills/       install-agent, workspace-config, brand-bible, wiki-ingest, wiki-ask, wiki-audit, yt-intel, yt-ask, yt-search, yt-corpus,
                seo-audit, seo-local, seo-ai-search, seo-page, seo-blog
  agents/       Claude subagents for Research Lead: youtube-scout, web-scout, trend-analyst, fact-checker
  examples/     sample config
```

No client data, credentials or machine paths live in this repo. Yours stay in your own workspace.

## Requirements

Python 3.10+ and `yt-dlp` for the YouTube skills. A Gemini API key is optional (videos without captions,
bulk corpus extraction) and must be your own. The SEO skills need only Python; a Google PageSpeed Insights
key is optional for speed checks and must be your own.

MIT licensed. The SEO skills adapt method from claude-seo and claude-blog by AgriciDaniel (MIT); see
[`plugins/bbm-agents/CREDITS.md`](plugins/bbm-agents/CREDITS.md).
