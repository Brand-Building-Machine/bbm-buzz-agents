---
name: seo-ai-search
description: Check and improve how likely the owner's business is to be found and cited in AI answers (ChatGPT search, Perplexity, Claude, Google AI Overviews and AI Mode, Copilot). Checks which AI crawlers robots.txt lets in (search vs training bots, told apart), whether content is visible without JavaScript, how quotable key pages are, entity and brand signals, and llms.txt; runs an optional manual visibility check with real customer questions. Use when the owner asks "does ChatGPT recommend us", "AI search", "GEO", "AEO", "AI Overviews", "llms.txt", "should I block AI bots", or was sold an "AI SEO" package. Read-only; drafts fixes for approval.
---

# seo-ai-search

## Start from the truth

Tell the owner this first, in plain words, because they are being sold otherwise:

- **AI search is still SEO.** Google's AI Overviews and AI Mode are built on Google's normal index and ranking. A page that ranks and answers the question well is what gets cited. There is no separate AI index to submit to.
- **Things you don't need for Google**: an `llms.txt` file, "chunking" content for AI, special AI phrasing, AI-specific markup, or planted mentions. Google has said so publicly.
- **What does matter**: being crawlable by the search bots, content that's in the raw HTML, clear direct answers, first-hand specifics competitors can't copy, and being mentioned by name on sites people trust (reviews, directories, local press, industry lists, real forum threads).
- **No one can guarantee AI citations.** Never promise one.

Uses `seo.py` from the `seo-audit` skill (folder next to this one): `python3 <seo-audit skill dir>/scripts/seo.py` (Windows: `python` / `py`).

## Flow

**1. Crawler access.** `seo.py site <url> --max-pages 5`. Read the robots.txt table. Each AI company runs separate bots for separate jobs; report search access and training access on **separate lines**, never merged:

| To appear in... | Needs this bot allowed | Not this one |
|---|---|---|
| ChatGPT search answers | `OAI-SearchBot` | `GPTBot` (training only) |
| Claude search answers | `Claude-SearchBot` | `ClaudeBot` (training only) |
| Perplexity | `PerplexityBot` | |
| Google Search, AI Overviews, AI Mode | `Googlebot` | `Google-Extended` (Gemini training/grounding only) |
| Siri, Spotlight, Safari | `Applebot` | `Applebot-Extended` (Apple Intelligence training only) |
| Copilot, and assistants using Bing | `Bingbot` | |

A blocked search bot is High. Blocking **training** bots (`GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`, `Bytespider`, `meta-externalagent`) is the owner's licensing choice: explain it, ask, don't decide. Blocking them does not remove the business from AI search.

How robots.txt groups work (the common mistake): a bot obeys only the most specific group that names it. If there's a `User-agent: GPTBot` group, the `User-agent: *` rules don't apply to GPTBot at all. A robots.txt that returns a server error (5xx) blocks everything.

Also: firewalls and CDN settings (for example Cloudflare's "block AI bots" toggle) can block search bots even when robots.txt allows them. You can't see that from outside; tell the owner where to look if AI tools say they can't read the site.

**2. Visible without JavaScript.** `seo.py page <url>` on the homepage and key service pages. Many AI fetchers don't run JavaScript. A `js_shell` or `js_or_empty` flag means the content is invisible to them: Critical for this skill.

**3. Quotability of key pages.** For the homepage, each core service page, and the top blog posts, score out of 15 (scale to 100 by x100/15):

| Check | Points | Full marks |
|---|---|---|
| Citable passages | 4 | 80%+ of important sections open with a self-contained answer: the claim, its support, and where it comes from, readable out of context (60-79% = 3, 40-59% = 2, 20-39% = 1) |
| Purpose fit | 3 | the intro says topic, audience and task; sections lead with the point; the format fits the question (1 each) |
| Entity clarity | 3 | one clear topic; the business, services and places named consistently; a plain "X is..." definition early for "what is" topics; the title matches the content |
| Structure | 3 | a short summary near the top, comparison tables with header rows, numbered steps for processes, definitions (4-5 present = 3) |
| Crawler access | 2 | from step 1: clean = 2, one issue = 1, Google blocked or several unintended blocks = 0 |

`seo.py text <file>` on a draft or saved page reports answer-sized sections and a summary box. Write the judgement yourself; don't fake precision.

**4. Entity and brand signals.** Is the business named the same way on its Google profile, LinkedIn, Facebook, industry directories, review sites, and in any local press or "best of <city>" lists? Organization or LocalBusiness schema with `sameAs` links to those profiles? A named person with credentials behind the content (Person schema)? Don't suggest a Wikipedia page unless the business is genuinely notable. Never create fake forum posts, reviews or mentions.

**5. llms.txt.** Report whether `/llms.txt` exists, with **zero weight**: no major AI search engine has said it uses it, and log studies show AI bots barely request it. If the owner wants one anyway, draft the minimal version:

```
# Business Name
> One sentence on what the business does, for whom, where.

## Main pages
- [Services](https://example.com/services): what we do
- [Contact](https://example.com/contact): phone, address, hours

## Key facts
- Licensed in <state>, licence <number>
```

**6. Visibility check (optional, manual).** Draft 8-10 questions real customers ask ("best employee benefits broker in <city>", "how do I set up a small group health plan in <state>", "<service> near <town>"). The owner (or you, if you have web access to these tools) asks each in ChatGPT, Perplexity and Google, and records: cited by name? which page? which competitors? Save the table; repeat monthly. Only report platforms that were actually checked. No paid tool, no score for unchecked platforms.

## Fixes to draft (owner approves)

- robots.txt changes, with the training-bot policy the owner chose. Example for "allow AI search, opt out of training":
  ```
  User-agent: GPTBot
  Disallow: /

  User-agent: Google-Extended
  Disallow: /

  User-agent: *
  Allow: /

  Sitemap: https://example.com/sitemap.xml
  ```
- Rewrites of weak sections into answer-first passages (hand bigger rewrites to `seo-page` or `seo-blog`).
- Organization/LocalBusiness schema with `sameAs`; Person schema for the named expert.
- Claim Bing Places and Bing Webmaster Tools (free; Bing's index feeds Copilot and some other assistants).
- The list of listings and mentions to go after, from `seo-local`'s citation list.

To keep Google from using a page's text in AI features, the controls are the normal snippet ones (`nosnippet`, `data-nosnippet`, `max-snippet`), which also affect regular results. Mention only if the owner asks.

## Report

`<reports folder>/YYYY-MM-DD-ai-search-<domain>.md`: the truth box (3 lines); crawler access (search vs training, separate); JS visibility; quotability score per page with the weakest sections quoted; entity signals; llms.txt (zero weight); visibility table if run; **top 5 actions** with who does each.

## Rules

- Never promise citations, rankings or traffic. Never quote third-party "AI traffic" statistics as fact.
- Never claim a named AI product reads llms.txt, or that `Google-Extended` affects Google Search.
- Where community advice contradicts Google's own documentation, follow Google and say so.
- Never write the site's robots.txt or any file on the site yourself. Draft; the owner applies.
- No em dashes in anything the owner will publish.

Method adapted from claude-seo and claude-blog by AgriciDaniel (MIT). See `CREDITS.md` in the plugin root.
