---
name: linkedin-carousel
description: Make a LinkedIn carousel (a PDF document post) from a topic, a post, a newsletter or notes. Picks a slide structure, writes a slide-by-slide brief for the owner to approve, then builds the slides one of three ways - designed in HTML with the brand's colours and fonts (free), generated whole by an image model on Fal or Higgsfield (paid, most creative), or hybrid (generated artwork with exact text on top). Renders the PDF and PNGs, checks every slide, and writes the post text that goes above it. Use when the owner says "make a carousel", "turn this into slides", "LinkedIn carousel", "document post", or linkedin-plan hands over a carousel slot. Drafts only; nothing is posted.
---

# linkedin-carousel

Two gates: the owner approves the **words** (the brief) before any design, and approves the **spend** before any paid image. Changing a sentence in a brief is free; regenerating ten images isn't.

Helpers: `linkedin.py` (in the **linkedin-post** skill's `scripts/`) for paths, work folders and the checker; `visuals.py` (in the **social-visuals** skill's `scripts/`) for rendering and image generation. `python3` on macOS/Linux, `python` or `py` on Windows. `linkedin.py paths` prints both locations.

## Before you start

1. `linkedin.py paths [--business <name>]`. Brand files are required: `voice-agent.md`, `brand-bible.md`, `root.css` (and `offers.md` if the last slide points at an offer). Missing → offer `brand-bible`. Read `linkedin.json` and `linkedin-stories.md` as in `linkedin-post`.
2. Get the source: the owner's topic, a post, a newsletter section, notes, or a story-bank entry. Ask for the real numbers or steps if the source doesn't have them.
3. **Route.** Use `linkedin.json` → `visuals.default` unless the owner asks otherwise:
   - `html`: free, exact text, brand fonts. Best for lists, steps and numbers.
   - `image`: every slide made by an image model. Most creative; words must be checked.
   - `hybrid`: the model makes the artwork, HTML puts exact text and the logo on top.
   For `image` or `hybrid`, `visuals.py keys` must show the provider ready. If not, offer `html` now and key setup (see **social-visuals**) for next time.

## Step 1: Brief (gate 1)

1. Pick the structure from `references/frameworks.md` and say why in one line.
2. `linkedin.py new carousel --slug "<topic>" [--business <name>]` makes the dated folder.
3. Write `slides.json` there:

```json
{
  "title": "Document title shown on LinkedIn",
  "structure": "Stack",
  "route": "html",
  "size": "1080x1350",
  "post": "The post text that goes above the carousel",
  "slides": [
    {"n": 1, "role": "cover", "headline": "...", "body": "...", "visual": "what's on the slide", "prompt": ""},
    {"n": 2, "role": "point", "headline": "...", "body": "...", "visual": "...", "prompt": ""},
    {"n": 6, "role": "close", "headline": "...", "body": "...", "visual": "...", "prompt": ""}
  ]
}
```

   Roles: `cover`, `context`, `point`, `stat`, `quote`, `proof`, `close`. Each list item or step is a `point` (the checker compares the count against a number on the cover). `prompt` is filled in Step 3 for `image`/`hybrid`.
4. Write the `post` text by the `linkedin-post` rules and edit pass: its own hook, 3-6 short paragraphs, why this carousel is worth swiping, a closing line. Links go in the first comment.
5. `linkedin.py lint slides.json` must report no errors.
6. **Show the owner the brief** as a numbered list (headline and body per slide) plus the post's first line. Wait for their okay or edits. Don't design before this.

## Step 2: Build (html and hybrid)

1. `visuals.py scaffold --kind carousel --out <folder>/slides.html --size <size> --brand-css <root.css>`.
2. Replace the example slides with the approved ones, one `<section class="slide <layout>">` each, using the template's layouts (`cover`, `point`, `stat`, `quote`, `list`, `close`). Footer on each slide: author from `linkedin.json`, page `n/total`. Logo: copy `logo.svg`/`logo.png` from the brand folder into the work folder and use it in the cover and close footers.
3. Keep the frame identical across inside slides. Text never smaller than 28px, source lines included (use the `source` class). Adjust sizes rather than overflow; a slide that doesn't fit is two slides.
4. **Hybrid:** first generate the artwork (Step 3), then put each image as the first child of its slide: `<img class="art" src="art/slide-02.png">`, with the text inside `<div class="panel">` placed on the calm area the prompt left empty (add `on-dark` to the slide for dark art). Never put text straight onto busy art.
5. `visuals.py render <folder>/slides.html --out <folder> --size <size> --pdf carousel.pdf`.

## Step 3: Generate (image and hybrid, gate 2)

1. Write `prompts.json` in the work folder following `social-visuals/references/image-prompts.md`: one shared style block built from `root.css`, then one prompt per slide (full slide with the exact words for `image`; artwork with **no text** for `hybrid`). Copy each prompt into `slides.json` too.
2. `visuals.py generate --provider <p> --prompts <folder>/prompts.json --out <folder>/art --aspect 4:5 --dry-run` (use `3:4` for models without 4:5).
3. **Ask the owner:** "This will make N images with <model> on your <provider> account. Price: <link from the dry run>. Go ahead?" Wait for yes.
4. Run it without `--dry-run`.
5. `image` route: `visuals.py pdf <folder>/art/slide-*.png --out <folder>/carousel.pdf --size <size>` (the image files may be `.jpg`; use the names `generate` printed).

## Step 4: Check every slide

`visuals.py inspect` the PNGs, then look at each one (see **social-visuals**, "Always inspect"). On the `image` route, read every word against `slides.json`; one misspelling means regenerate that slide only. On any route: nothing cut off, readable at phone size, same frame throughout, the cover works alone. Fix, re-render, re-check. Couldn't view images → say so and ask the owner to check.

## Output (in the work folder)

- `slides.json` (the approved brief and post text), `carousel.pdf` (what gets uploaded), `slide-NN.png` or `art/` images, `slides.html` (html/hybrid), `prompts.json` + `art/generation.json` (image/hybrid).
- `README.md`: the post text ready to paste, the document title, the first comment, and upload steps: *Start a post → the "+" or "More" icon → Add a document → choose carousel.pdf → add the title → paste the post text → Post.*

No em dashes in anything you write for the owner, including README and plan files (use a comma, colon or full stop).

## Report to the owner

A top-level message: topic, structure, slide count, route (and images generated, if any), the post's first line, the path to `carousel.pdf`, anything left to check, and "from linkedin-carousel". Attach or link the cover PNG if the channel supports it.

## Limits

Drafts only: never post, schedule or upload. No paid generation without the owner's yes on count and model. Never invent statistics, results or customer stories; unknowns are `[Client to provide]` in the brief and are resolved before building. No real people's faces or other companies' logos in generated images.
