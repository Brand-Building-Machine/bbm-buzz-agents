---
name: social-visuals
description: The rendering and image-generation engine behind the social media skills. Turns HTML slides into exact-size PNGs and a PDF using the owner's own Chrome or Edge (free), stitches images into a PDF, and generates images with Fal or Higgsfield on the owner's own key (paid, only after their yes). Use when linkedin-carousel or linkedin-image needs to render or generate, or when the owner says "render these slides", "make this a PDF", "set up my image key", "which image models can I use".
---

# social-visuals

The engine is `scripts/visuals.py` in this skill's folder (`python3` on macOS/Linux, `python` or `py` on Windows). Starter slide templates are in `templates/`. Prompt-writing and model guidance: `references/image-prompts.md`.

## Rendering HTML (free)

1. `visuals.py browser` shows which browser will render. None found → the owner installs Google Chrome (or sets `BBM_BROWSER` to the full path of Chrome or Edge), or uses the image route.
2. `visuals.py scaffold --kind carousel|single --out <file>.html --size 1080x1350 --brand-css <brand folder>/root.css` writes a starter with the brand's colours and fonts built in. Edit the content; keep one frame for the whole carousel.
3. Each slide is a **top-level `<section class="slide ...">`**; nothing outside a slide is rendered. Don't nest sections. Layout classes in the template: `cover`, `point`, `stat`, `quote`, `list`, `close` (carousel) and `framework` (single); `source` for a number's source line. Text over generated art: `<img class="art" src="...">` as the slide's first child, the text inside a `<div class="panel">`, and `on-dark` on the slide when the art is dark. Images by relative path from the HTML file (the logo: copy it next to the HTML).
4. `visuals.py render <file>.html --out <folder> --size 1080x1350` → `slide-01.png` ... and `<file>.pdf`. `--no-pdf` for a single image, `--no-png` for PDF only.

## Generating images (paid)

1. `visuals.py keys` shows which provider is ready (never the key). None → `visuals.py keys init`, then the owner pastes their own key into the file it names. Never ask them to paste a key into chat; if they do anyway, don't repeat it, and suggest they rotate it.
2. Write the prompts file: `[{"name": "slide-01", "prompt": "..."}]`, one entry per image, following `references/image-prompts.md`.
3. `visuals.py generate --provider fal|higgsfield --prompts prompts.json --out <folder> --aspect 4:5 --dry-run`. Show the owner the count, model and price link; **wait for their yes.**
4. Same command without `--dry-run`. Every attempt is logged to `generation.json` in the output folder. Failed images are listed; regenerate just those with a prompts file of the failures.

## Always inspect

`visuals.py inspect <files>` prints pixel sizes. Then **look at every image** if you can view images: exact spelling of every word, nothing cut off at the edges, text readable at phone size (about 360 pixels wide), brand colours, nothing extra (stray words, fake logos, watermarks, warped hands). Fix and re-render or regenerate what fails. If you can't view images, say so and ask the owner to check them; never call a visual checked when it wasn't.

## Limits

Never posts or uploads anything. Never spends without the owner's yes on the count and model. Never stores, prints or commits keys. Never generates real people's likenesses, other brands' logos or copyrighted characters.
