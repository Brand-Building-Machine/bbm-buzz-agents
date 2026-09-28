---
name: landing-page
description: Build a landing page or small website that converts and doesn't look AI-made, for any business with a brand folder. Runs the full method: page brief, offer and CTA, visible reference directions, design rules, real assets, hero first, full page, separate copy pass, fresh-context critics, QA gate, preview approval. Uses the impeccable skill for design craft and the cro, copywriting, copy-editing, offers and lead-magnets skills for conversion. Use for "build a landing page for...", "make a page for this offer/ad/campaign", "rebuild my website", "a page for my FSBO sellers", etc. SEO is handed off, not done here.
---

# landing-page

The method behind Web Studio. It comes from a 12-video study of how the best AI-assisted designers actually build (only what they demonstrated, not what they claimed), paid-search landing page research, and head-to-head tests of design skills on real client briefs.

**The two failures this prevents:** pages that work but look AI-made, and pages that look good but don't convert. Functional checks never prove visual quality, and a pretty page with a weak ask is still a failure.

## Before you start

- **Brand folder first.** Read `BRAND_PATH` from the owner's config (`brand-bible.md`, `voice-agent.md`, `offers.md`, `root.css`, plus any logos/photos next to them). If it doesn't exist, stop and run the `brand-bible` skill. **The brand always wins** over any default in impeccable or the conversion skills (fonts, colours, words, claims).
- **Where the work goes:** `SITES_PATH` from the config, one folder per page: `<SITES_PATH>/<business>/<page-slug>/` holding `brief.md`, `references/`, `page-rules.md`, `assets/`, `index.html` (+ css/js), `qa/`. If `SITES_PATH` is missing, run `workspace-config`.
- **Impeccable context:** impeccable looks for `PRODUCT.md` and `DESIGN.md`. Write both into the page folder at step 1: `PRODUCT.md` = who it's for, the offer, the one conversion, proof, voice (a one-page digest of the brand folder); `DESIGN.md` = the brand tokens from `root.css`, logo rules, photo direction, plus the page rules once step 4 exists. Point to the brand files; don't duplicate them. impeccable's own rule is "the brief wins": treat the brand folder as the brief.
- **Never invent** prices, guarantees, reviews, numbers, names, licences or results. Missing = a labelled placeholder on the launch-blocker list.

## The method (11 steps, 4 owner checkpoints)

**1. Page brief.** Write `brief.md` in 6 lines: Pain / Person / Promise; traffic source and intent; the one conversion event; what the visitor already knows; top 3 objections; proof on hand. Pick the page structure by traffic type (see `references/conversion-rules.md`). Write PRODUCT.md and DESIGN.md.
**Checkpoint 1:** the owner confirms the brief in one reply.

**2. Offer and CTA.** From `offers.md` (and the `offers` / `lead-magnets` skills if the offer itself is weak): the conversion mechanism (call, form, booking, application), CTA copy as verb + what they get, the form fields (default 3: name, phone, email; qualify with one tappable question first only if it matters), what happens after they submit, the privacy line. Guarantee process or price, never outcomes.

**3. References: show, don't ask.** Pull 6-10 candidate live sites from free galleries (`references/resources.md`), filtered by niche and audience. Screenshot each at 1440 and 375. Present **2-3 directions**, each = 1 primary reference (layout and feel) + 1-2 secondaries for named components, with one line on what to carry and one on what to avoid. Never clone a site. For small local businesses, include at least one direction from real local-service sites, not only design-award sites.
**Checkpoint 2:** the owner picks a direction or says "none of these". They react to screenshots; they never write a design brief.

**4. Design rules: measure, don't describe.** From the chosen reference, write `page-rules.md` in numbers: type scale ratio, display weight and tracking, spacing rhythm, radius and shadow ladder, palette proportions, image treatment, motion timing, and what it refuses to do. Map them onto the brand: fonts, colours and logo from the brand folder; proportion and rhythm from the reference. Add 5-10 "tests a bad copy would fail". Then read impeccable's `reference/craft-floor.md` before any UI work.

**5. Assets before build.** List every asset. Order: the business's real photos, team, logos, reviews, numbers → one icon set, never mixed → a licensed font only if the brand has none → optional paid image generation only with the owner's yes, piloted on one image first. Every placeholder goes on the launch-blocker list in `assets.md`.

**6. Hero + first transition only.** Build the hero and its handoff into section 2, at 375 and 1440 together. Static HTML/CSS/vanilla JS with the brand tokens. The hero must visibly bleed into section 2 (no false floor). Screenshot it next to the reference. Run the craft critic on this slice only.
**Checkpoint 3:** the owner sees the hero beside the reference and approves or redirects **before** the rest is built. Cheapest place to change direction.

**7. Full page.** Section order from the traffic-type structure. One job per section. **One signature moment** (a single meaningful interaction or visual idea tied to the story, e.g. a SOLD sign, a before/after bar) plus subtle reveals; all motion behind `prefers-reduced-motion`. Use impeccable's new-work playbook and refuse rules (no eyebrow labels over every heading, no rows of identical icon cards, no big-stat tiles as decoration). Multi-page sites: sitemap + grey-box wireframes first, then build every page a buyer clicks.

**8. Copy pass (separate from the build).** Use the `copywriting` and `copy-editing` skills against `voice-agent.md`: pain named first, one ask per screen, specifics instead of adjectives, 5th-7th grade reading level, every number traced to the brand folder, the brand's banned words and no em dashes. Output a before/after table in `qa/copy-pass.md`.

**9. Critics: fresh context, capped.** Four critics, each in a **fresh subagent** that never saw the build conversation, each given only the page, the brief, the brand folder and its checklist:
- **Conversion critic** (`cro` skill): one goal, 3-second hero, CTA clarity, form friction, objection coverage, mobile call path.
- **Brand critic**: exact tokens, logo rules, proof wording, banned words, compliance lines.
- **Craft critic** (impeccable `critique` / `audit`): hierarchy, rhythm, the refuse rules, the page-rules tests, screenshot review at 375 and 1440.
- **Copy critic** (`copy-editing`): slop tells, specificity, voice.
Each returns **located defects** ("hero subhead, 375px: wraps to 5 lines"), marked must-fix or nice-to-have. No scores. Fix all must-fix; **max 3 rounds**, then stop and show the owner the open defects. On a runtime without subagents, run them one at a time and label the review "same-session, not independent".

**10. QA gate.** Run the `page-qa` skill in ship mode. It must pass: no placeholders, a working lead path, no overflow at 375/768/1024/1440, labels, one H1, no em dashes. Then look at its screenshots yourself (hard cuts between sections, wrong logos, invented facts). Test the form end to end into the real destination and the `tel:` link on a phone. Save the report in `qa/`.

**11. Preview, approval, ship.** Deploy to a preview URL (or hand the folder over) and get **Checkpoint 4: the owner approves the preview.** Nothing goes to production without it; deploying and publishing are the owner's call. Then save what worked (page rules, components, the signature idea) into the brand folder as a reusable style note. Hand metadata and indexing to the SEO Desk.

## Rules

- The brand folder wins. Then the brief. Then impeccable and the conversion skills.
- One conversion goal per page. The call or form is reachable from the first screen on a phone.
- No stock photos of fake people. No invented social proof. Placeholders are labelled and block launch.
- Don't load every reference file of every skill up front. Read what the current step needs.
- Owner unavailable or in a test run? Say so, record your assumption at each checkpoint in `brief.md`, and keep going; never skip the QA gate.
