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
| **Meta Ads Desk** | Facebook and Instagram lead ads: audits results, writes new ads, plans changes you approve, checks tracking. Nothing spends without your yes | Claude or Codex |
| **Email Desk** | Your emails in your voice: lead magnet and welcome sequences, sales sequences, follow-ups after calls and proposals, new-client onboarding, cold outreach. Drafts only | Claude or Codex |
| **Web Studio** | Landing pages and small websites that convert and don't look AI-made: brief, visible directions to pick from, hero first, fresh-eyes critics, QA gate. You approve before anything goes live | Claude |
| **LinkedIn Desk** | LinkedIn posts, carousels and images in your voice, built on your real stories and numbers, plus a weekly plan. Slides designed with your brand for free, or made by an image model (Fal or Higgsfield) on your own account. Drafts only; never posts | Claude or Codex |
| **Google Ads Desk** | Plans your Google Ads like an agency onboarding (keywords from Google's own planner, structure, budget, tracking, ads) and audits what's running. Read-only; never changes the account | Claude or Codex |

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
| `meta-audit` | Reads your Meta lead ads (live via Meta's connector, or an Ads Manager export): which ads to keep, cut, fix or scale, judged on cost per qualified lead |
| `meta-creative` | Turns your reviews and customer words into distinct ad concepts: hooks, copy, lead-form questions and a design brief for each |
| `meta-launch` | Writes every change as a plan with a plan id; applies only the plan you approve, everything created paused, then confirms it |
| `meta-tracking` | Checks leads actually arrive and Meta learns from real leads: forms, pixel, Conversions API, duplicates |
| `email-sequences` | Lead magnet delivery, welcome and nurture, sales sequences, a 5-day email course, re-engaging a quiet list. Also builds your email voice from emails you've sent |
| `email-followups` | Same-day call recaps, no-shows, proposals gone quiet, leads gone cold, the close-the-loop email, and how to answer a reply |
| `email-onboarding` | After a client signs: welcome, what we need from you (safely), kickoff, first win, 30-day check-in, and a review ask timed to a real win |
| `email-cold-outbound` | Cold outreach to prospects you choose: a true hook per prospect, a short sequence, reply handling, and the compliance basics. Never sends or scrapes |
| `google-ads-setup` | Agency-style onboarding interview, a search-demand and budget check, keyword research with Google Keyword Planner, then a checked campaign blueprint and a step-by-step build sheet |
| `google-ads-audit` | Reads your Google Ads account (read-only, through your Composio connection) and scores 14 areas: tracking, structure, budgets, bidding, keywords, Quality Score, wasted search terms, ads, assets, landing pages. Top fixes and a 7-day plan |
| `landing-page` | Web Studio's method: page brief, offer and CTA, reference directions, design rules, real assets, hero first, full page, copy pass, critics, QA, preview approval |
| `page-qa` | Pre-launch gate for a page: placeholders, a working lead path, overflow at 4 screen widths, labels, basics, screenshots |
| `impeccable` | Design craft (by Paul Bakaus, Apache-2.0): shape, critique, audit, polish. Your brand always wins over its defaults |
| `cro` · `copywriting` · `copy-editing` · `offers` · `lead-magnets` | Conversion and copy (from Corey Haines' marketingskills, MIT). They read your brand folder as their context |
| `linkedin-post` | Writes a LinkedIn post from your real stories: one proven formula, two first lines to pick from, an edit pass that strips AI tells, and a copy check |
| `linkedin-carousel` | Turns a topic or post into a carousel (PDF document post): slide brief you approve, then built in HTML with your brand (free), by an image model, or both, and checked slide by slide |
| `linkedin-image` | One graphic for a post: framework, big number or quote card in your brand (free), or an illustration from an image model |
| `linkedin-plan` | Sets up your LinkedIn profile, then plans a week of posts (or a bank of ideas), each tied to a real story |
| `linkedin-stories` | Interviews you and keeps your story bank: numbers, stories, opinions, mistakes and your own writing. Every LinkedIn skill reads it |
| `social-visuals` | The engine: renders slides to PNG and PDF with your own Chrome or Edge, and generates images on Fal or Higgsfield with your own key, only after your yes |
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
- "Install SEO Desk" / "Install Meta Ads Desk" / "Install Email Desk" → same
- "Are my agents up to date?" → offers updates as drafts

## Updates

Clients track the `release` branch. Claude Code pulls it automatically (loads next session). Codex refreshes git
marketplaces at startup; to force it: `codex plugin marketplace upgrade`. Persona updates never apply
themselves — `install-agent` offers them as drafts for you to approve.

## What's inside

```
plugins/bbm-agents/
  personas/     the ten agents (templates with {{PLACEHOLDERS}})
  skills/       install-agent, workspace-config, brand-bible, wiki-ingest, wiki-ask, wiki-audit, yt-intel, yt-ask, yt-search, yt-corpus,
                seo-audit, seo-local, seo-ai-search, seo-page, seo-blog,
                meta-audit, meta-creative, meta-launch, meta-tracking,
                email-sequences, email-followups, email-onboarding, email-cold-outbound,
                google-ads-setup, google-ads-audit,
                linkedin-post, linkedin-carousel, linkedin-image, linkedin-plan, linkedin-stories, social-visuals
  agents/       Claude subagents for Research Lead: youtube-scout, web-scout, trend-analyst, fact-checker
  examples/     sample config
```

No client data, credentials or machine paths live in this repo. Yours stay in your own workspace.

## Requirements

Python 3.10+ and `yt-dlp` for the YouTube skills. A Gemini API key is optional (videos without captions,
bulk corpus extraction) and must be your own. The SEO skills need only Python; a Google PageSpeed Insights
key is optional for speed checks and must be your own. The Meta skills need only Python; live account access
is Meta's own ads connector (`https://mcp.facebook.com/ads`, sign in with your Meta login), optional because an
Ads Manager export works too. The email skills need only Python and never send anything.

The Google Ads skills need only Python and the free Composio CLI (`composio link googleads`; on Windows it runs inside
WSL). Access is read-only. Without Composio the audit works from Google Ads exports.

The LinkedIn skills need only Python. Designed slides and images render with your own Google Chrome or Microsoft
Edge (free). Image-model visuals are optional and use your own Fal or Higgsfield key, kept in `~/.bbm-agents.env`
on your computer; nothing is generated (or charged) without your yes. Nothing is ever posted to LinkedIn.

MIT licensed. The SEO skills adapt method from claude-seo and claude-blog by AgriciDaniel (MIT); the Meta skills from
Motion, Corey Haines, Mathias Chu, hyperfx.ai (MIT) and LangChain (Apache-2.0); the email skills from Anthropic's knowledge-work-plugins (Apache-2.0), GrowthEngineX, Corey Haines and George Hartley (MIT); the Google Ads skills from Optmyzr (Apache-2.0), AgriciDaniel's claude-ads and Corey Haines (MIT); the LinkedIn skills from Sergey Bulaev, Charlie Hills and Corey Haines (MIT); see
[`plugins/bbm-agents/CREDITS.md`](plugins/bbm-agents/CREDITS.md).
