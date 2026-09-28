---
name: page-qa
description: Run the pre-launch QA gate on a built landing page or site folder. Checks for leftover placeholders, lead capture that actually works (form endpoints, labels, a real phone link), page basics (lang, viewport, title, one h1, alt text, no em dashes), missing local files, and, when Chrome is installed, sideways scrolling on phones, small tap targets and screenshots. Use when the owner says "QA this page", "is this ready to launch", "check the landing page before it goes live", or after building a page and before handing it over. Read-only; never edits the page.
---

# page-qa

A pass/fail gate for a static page before anyone sees it. Facts come from `scripts/page_qa.py`; fixing is a separate step the owner approves.

The script is `scripts/page_qa.py`, relative to this skill's folder. Run it with `python3` on macOS/Linux, `python` or `py` on Windows.

## Run it

```
page_qa.py <page folder or index.html> [--mode draft|ship] [--out qa-report.md] [--json]
```

- A folder means its `index.html`. For a multi-page site, run it once per page.
- `--out` sets the report path (default: `qa-report.md` next to the page). Screenshots `shot-1440.png` and `shot-375.png` are written next to the report. Point `--out` somewhere else if the page folder should stay clean.
- `--json` prints machine-readable results. `--no-render` skips the browser checks. `--chrome <path>` (or the `PAGE_QA_CHROME` environment variable) points at a browser in an unusual place.
- Exit code: `0` pass (warnings allowed), `1` fail, `2` bad arguments or no page found.

## Draft vs ship

- **draft** (default): the page is still being built. Placeholders (a `REPLACE_ME` form endpoint, `[phone]`, a dummy `tel:` number) are listed as warnings so the build can move on.
- **ship**: the page is about to go live. Any placeholder is a FAIL. Use this mode before anything is published or handed to a client.

Everything else fails the same way in both modes.

## What each check means

1. **Placeholders**: `REPLACE_ME`, `{{...}}`, lorem ipsum, TODO, TBD, `[Client to provide]`, `[phone]`, `000-000` numbers, `tel:+10000000000`, example.com. Checked in visible text, attributes, inline scripts and the page's own JS files.
2. **Lead capture**: every form posts (method POST) to an absolute http(s) URL, or declares a `data-endpoint`. Every required field has a label (`label for`, a wrapping label, or `aria-label`). `tel:` links must be real-looking numbers. A page with no form, no phone link, no email link and no booking link fails: nobody can convert. No `tel:` link at all is a warning.
3. **Basics**: `<html lang>`, a viewport meta tag, a title, exactly one `<h1>`, alt text on every image (empty alt only when marked decorative with `role="presentation"`, or inside a link that has an `aria-label`), no em dash in visible text. A missing meta description and `href="#"` dead links are warnings.
4. **Local references**: every local CSS, JS, image, font and linked page (including `url()` inside local CSS) exists on disk.
5. **Horizontal overflow**: the page is rendered at 375, 768, 1024 and 1440 px wide. Any sideways scroll fails, with the element sticking out furthest named.
6. **Tap targets**: at 375 px, links, buttons and inputs smaller than 44x44 px. A warning with examples; inline links inside sentences are not counted.
7. **Screenshots**: `shot-1440.png` (1440x3200) and `shot-375.png` (the page laid out at 375 px, scaled up to fill a 500 px wide image). Look at them before calling the page done.

Checks 5 to 7 need Google Chrome, Chromium or Microsoft Edge. Without one they are reported as a warning ("rendered checks skipped: no Chrome"), never as a pass. Say so in your summary and ask the owner to look at the page on a phone.

## What to do with the result

1. Give the owner the one-line verdict and the failures in plain words, most serious first. Link the report and the screenshots.
2. Look at both screenshots yourself if you can view images: the script cannot judge whether the page looks right.
3. For each FAIL, say what fixes it and who fixes it. Placeholders usually need something from the owner (the real phone number, the form endpoint): ask for exactly what is missing.
4. Do not edit the page unless the owner says yes. After fixes, run the script again; a page is ready only when ship mode passes.
5. Never report a page as launch-ready from draft mode, or when the rendered checks were skipped, without saying so.
