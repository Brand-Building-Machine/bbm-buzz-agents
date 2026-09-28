---
name: brand-bible
description: Build or update the owner's brand bible — the standing truth every other agent reads before it writes, designs or sells. Produces four files per business (brand-bible.md, voice-agent.md, offers.md, root.css) plus a viewable brand-sheet.html, through a short interview with the owner, prefilled from their website and existing documents. Use when the owner says "build my brand bible", "set up my brand", "update my brand/offers/voice/colours", or when another skill needs brand files that don't exist yet.
---

# brand-bible

The brand bible is the foundation: landing pages, content, emails and ads all read it. A thin or wrong brand bible makes everything downstream generic. **Complete beats long.** A tight, true 3,000 words beats a padded 15,000.

The script is `scripts/brand.py`, relative to this skill's folder (the folder containing this SKILL.md). Run it with `python3` on macOS/Linux, `python` or `py` on Windows.

## What you produce (per business)

| File | What it holds | Who reads it |
|---|---|---|
| `brand-bible.md` | Company, offers summary, customer + personas, positioning + approved facts, voice summary, visual identity, compliance, open items | Everything |
| `voice-agent.md` | Tone, do/don't, words to use and avoid, proprietary truths, learned preferences | Anything that writes |
| `offers.md` | Every service/product: who, price, included, steps, proof, guarantee, the ask | Pages, ads, quotes |
| `root.css` | Exact colours, fonts, radius as CSS variables | Anything visual |
| `brand-sheet.html` | Generated view of root.css for the owner to eyeball | The owner |

Where they go: `BRAND_PATH` in the owner's config. `python3 <skill dir>/scripts/brand.py paths` shows it. If it contains `{business}`, the owner runs several businesses and each gets its own brand folder; always ask which business you're working on. If `BRAND_PATH` is missing, run `workspace-config` first.

## Source priority — never invent

1. **What the owner tells you** in this conversation.
2. **The owner's existing documents** — brand guides, old brand files, pitch decks, past copy, reviews exports, meeting notes in their workspace. Search the workspace (and its map) before asking.
3. **Their website and public profiles** (Google Business, reviews) — prefill only; the owner confirms.

Anything none of these gives you stays `[Client to provide]` and gets listed in Open items. Never invent a founder, a year, a number, a review count, a licence, a guarantee or a price.

## Flow

**1. Setup.** Confirm the business and brand name. `brand.py scaffold --name "<Brand>" [--business <name>] [--website <url>]` creates the folder and blank templates. It never overwrites; if files exist, you're **updating**, so read them first and change only what the owner changes.

**2. Gather before you ask.** Read the owner's existing documents and the website (home, about, services, reviews, contact). Pull real phrases customers and the owner use. Note what you found and where.

**3. Interview — rounds, not a form.** Ask in rounds of 2-3 related questions, each with your recommended answer from step 2, so the owner corrects instead of composing. Four rounds is typical:
- **Round 1 — the business:** one-liner, service area, story, proof (licences, years, reviews, guarantees).
- **Round 2 — offers and customers:** each offer and its price/range and the ask; who buys, what makes them call, who they're not for.
- **Round 3 — position and voice:** why us over the alternatives; how they talk (show 2 sample lines in two different tones and let them pick); words they'd never use.
- **Round 4 — look:** see step 5.
Skip any question the documents already answer confidently — say "I'm using X from your <source>" instead.

**4. Write the three markdown files** from the templates. Fill every `{{SLOT}}`. Delete the `<!-- guidance -->` comments as you fill each part. Add personas (2-4) and offers (one `## Offer:` block each). Use the owner's words over polished ones. No em dashes anywhere.

**5. Colours, fonts, logo — the owner confirms, you don't guess.** Models are unreliable at extracting exact brand colours. Propose what you found on the site (hex codes and font names), and ask the owner to confirm or paste the real ones. Ask them to drop their logo file(s) into the brand folder as `logo.png` / `logo.svg`. Then fill `root.css`: the four required colours, the two fonts, the radius; delete optional lines that don't apply. Fix the `@import` line for their fonts (or delete it if they're system fonts).

**6. Brand sheet.** `brand.py sheet [--business <name>]` builds `brand-sheet.html`. Ask the owner to open it and say whether it looks like them. Adjust root.css until it does.

**7. Gate.** `brand.py check [--business <name>]` must print `PASS`. It checks: all four files, every section present and filled, at least one persona and one offer, no placeholders left, no em dashes, valid colours, and readable text contrast. `[Client to provide]` is allowed — it's reported, and every one must be listed in the bible's Open items.

**8. Report to the owner** in a few lines: where the files are, what's still `[Client to provide]` and who should supply it, and one sentence on how other agents will use it ("landing pages and posts now pull your voice and colours from here").

**9. Commit** the brand folder only, and only if the workspace lets agents commit. Push only if the workspace rules say agents push.

## Updating later

Owner says "we raised prices", "new service", "we don't say X anymore", "that ad was off-brand": update the one file it belongs to (offers → `offers.md`; voice feedback → `voice-agent.md` Learned preferences with the date), bump `updated:` in the frontmatter, re-run `check`. Never rewrite the whole set for a small change.

## Rules

- Complete, not long. If a section is getting padded, it's wrong.
- One business per brand folder. Never mix two businesses' facts.
- Approved facts are exact: "4.9 stars from 212 Google reviews (Sep 2026)", never "nearly 5 stars from hundreds of reviews".
- The brand bible is standing truth. Moving things (this month's promo, current ad results) don't belong here.
