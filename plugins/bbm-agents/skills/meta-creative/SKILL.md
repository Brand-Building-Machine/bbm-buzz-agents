---
name: meta-creative
description: Plan and write Facebook and Instagram lead ads in the owner's voice. Mines their reviews and customer language, maps pains to the people who feel them, picks angles, and writes a batch of distinct ad concepts, each with hooks, primary text, headline, description, call to action, instant-form questions and a design brief for whoever makes the image or video. Lead generation focus. Use when the owner says "write me some Facebook ads", "I need new ads", "my ads are tired", "what should my ads say", "give me ad ideas", or meta-audit says to replace ads. Drafts only; nothing is uploaded.
---

# meta-creative

On Meta today the ad does the targeting: the account targets broadly and the creative decides who stops. So the job is not "write an ad"; it is "find the right people's exact problem and say it in their words, several different ways". Method adapted from Motion's creative-strategy skills (MIT), made Meta- and lead-gen-specific.

## Before you start

1. `meta.py paths [--business <name>]` (the script is in the **meta-audit** skill's folder, `scripts/meta.py`; `python3` on macOS/Linux, `python` or `py` on Windows). Drafts go in the reports folder it prints.
2. **Brand files are required.** Read `brand-bible.md` (customer, positioning, proof), `voice-agent.md` (how they sound), `offers.md` (what the ad sells, price, guarantee). Missing → stop and offer `brand-bible`. Never write copy in an invented voice, and never invent facts.
3. Read `meta-ads.json` if it exists: `qualified_lead_means` (who the ads must attract), `lead_method` (instant form or website), `special_ad_categories`.
4. Read the last audit in the reports folder if there is one. Winners tell you what to iterate on; kills tell you what not to repeat.
5. **Ask for the offer if it isn't obvious.** Lead ads need a reason to raise a hand: a free review, quote, assessment, consultation, guide or checklist. "Contact us" is not an offer.

## Step 1: Customer language (do this first)

Best source: their reviews (Google, Facebook, Yelp, testimonials in the brand bible, or text the owner pastes). Second: sales-call notes, FAQs, emails. Follow `references/strategy.md` §1:
- Score each review 1-5 for usefulness; drop the 1s; quote only from 4s and 5s.
- Pull into five buckets: pain points, trigger moments ("what made them call"), objections before buying, transformations (before → after), and ad-ready phrases, word for word.

No reviews at all → ask the owner 5 questions from `references/strategy.md` §1 and say the batch rests on their memory, not customer words.

## Step 2: Strategy map

Follow `references/strategy.md` §2-5:
1. **Anchor:** pain (almost every service business) or desire.
2. **Personas:** 2-4 people who feel the pain in different life contexts. For lead gen, only people who can become *qualified* leads.
3. **Angles:** one conversational truth per pain x persona ("Your broker only calls at renewal"). Not a slogan.
4. **Awareness stage** for each angle: cold traffic is mostly problem-aware; retargeting is product-aware.

Show the map to the owner as a short table and get a nod before writing. This is where they correct you cheaply.

## Step 3: Concepts

Write **3-6 concepts** (more than the budget can test is waste; `meta.py tcpl` says how many ads the budget feeds). Each concept is one angle x one mechanic x one format. **Make them genuinely different:** Meta's delivery system groups near-identical ads and treats them as one, so five rewordings of the same idea earn less reach than three different ideas. Vary the angle and the format across the batch; never the same format twice.

For each concept: pick a **mechanic** and a **format** from `references/hooks.md` and `references/formats.md`, then write:
- **Hooks:** for video, all three parts (first frame, first spoken line, on-screen text), which must not repeat each other; for a static, the image headline plus the first line of primary text. Three hook options per concept, each using a different trigger.
- **Primary text:** the hook in the first line (under ~125 characters, before "See more"), then the problem, the offer, and **who it's for / not for** (filters out bad leads), then the call to action. Short (40-90 words) is the default; long story copy when the angle needs it.
- **Headline** (under 40 characters) and **description** (under 30).
- **Call to action button:** Get Quote, Book Now, Sign Up, Learn More, Apply Now, Contact Us. Match the offer.
- **Instant form** (when `lead_method` is instant form): intro line, 1-3 qualifying questions, easiest first, and the thank-you message saying exactly what happens next and when. See `references/formats.md` §3.
- **Design brief** for whoever makes the visual (the owner, their designer, or a design tool): format, aspect ratios, what's in the frame, on-image text (max ~7 words), brand colours from `root.css`, and what to avoid. For video: a shot list with the hook in the first 2 seconds.

## Step 4: Check before showing

- `meta.py copy <draft file>` must report no errors. It checks em dashes, lengths, placeholders, all-caps and "Introducing/Discover" openers, and warns on copy that might imply the viewer's personal attributes ("Are you in debt?"). Meta rejects that; rewrite about the situation ("Debt piling up?").
- Every claim traces to the brand files or the owner. Missing proof → `[Client to provide]`, never a guessed number, review count, result or guarantee.
- If `special_ad_categories` is set (financial services and insurance, jobs, housing, social issues): no age, gender or zip targeting will be possible, so the copy must do all the filtering.
- Read each hook out loud. If it sounds like an ad, rewrite it.

## Output

Save to `<reports folder>/YYYY-MM-DD-creative-<slug>.md`:

```
# Meta ad concepts: <business>, <offer> (<date>)
Offer: <what they get> | Lead method: <instant form / website> | Special category: <none / which>

## Strategy map
| Pain | Persona | Angle | Awareness |

## Concept 1: <name>
Angle: ... | Mechanic: ... | Format: ... | Aspect ratios: 4:5 + 9:16
Hooks: 1) ... 2) ... 3) ...
Primary text: ...
Headline: ...
Description: ...
Button: ...
Form: intro / questions / thank-you (instant form only)
Design brief: ...
Why this should work: <one line tied to a review quote or insight>

## Concept 2 ...

## Test plan
<Which concepts to launch first and why; how many the budget can feed; what "winning" means (the target cost per qualified lead).>
```

Use the `Primary text:` / `Headline:` / `Description:` labels exactly; `meta.py copy` reads them.

## Report to the owner

A top-level message: the offer and the number of concepts, a one-line summary of each (angle and format), which 2-3 to launch first, the path to the file, and "from meta-creative". Next step: once they pick and the visuals exist, `meta-launch` builds them paused for approval.

## Limits

Drafts only. Never upload, publish or boost. Never make up testimonials, reviews, results, prices or credentials. No before/after claims about bodies, health or money that Meta's policies prohibit; when unsure, say so and suggest the owner check Meta's advertising standards.
