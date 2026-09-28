# Image prompts and models

## Which route

| Route | What it makes | Cost | Best for |
|---|---|---|---|
| `html` | Slides designed in HTML with the brand's `root.css`, rendered by the owner's own browser | Free | Frameworks, lists, steps, numbers, anything where exact text matters |
| `image` | Whole slide or graphic made by an image model, text included | Paid, owner's key | Bold, illustrated, photographic or unusual looks |
| `hybrid` | Image model makes the artwork only; the text and logo are laid over it in HTML | Paid, owner's key | Creative look **and** guaranteed-correct text |

When in doubt, `hybrid` gives the creative look without risking a misspelled headline. On the `image` route, check every word on every slide.

## Models

Only the provider the owner has a key for. Prices change; send the owner to the model page to check before a big batch (`generate --dry-run` prints the link).

| Provider | Model id | Good at | Notes |
|---|---|---|---|
| Fal | `fal-ai/nano-banana-pro` (default) | Exact text inside images, clean design, brand colours | Aspect 1:1, 4:5, 3:4, 2:3, 9:16 and others |
| Higgsfield | `ideogram/v4.0` (default) | Typography-heavy designs, posters, text | Aspect 1:1, 4:5, 9:16, 16:9 and more |
| Higgsfield | `recraft/v4.1/text-to-image` | Flat illustration, vector-style graphics, icons | Aspect includes 4:5; `resolution` is set to `1k` automatically |
| Higgsfield | `higgsfield-ai/soul/standard` | Photographic, people and places | **No 4:5**: use `--aspect 3:4` and let the PDF crop |

Other models on either platform work with `--model <id>`; extra settings with `--param key=value`.

## Writing a prompt

Every prompt in a set shares one **style block**, pasted word for word, so the slides look like one carousel. Build it once from `root.css` and `brand-bible.md`:

```
Style: <flat editorial / bold poster / soft illustration / photographic>.
Colours: background <hex>, main <hex>, accent <hex>, text <hex>. No other colours.
Type: <heavy serif / clean geometric sans> headline, generous margins, lots of empty space.
Never: logos, watermarks, signatures, extra words, borders, stock-photo people, emoji.
```

Then per image:

**Full slide (`image` route)**
```
<Style block>
LinkedIn carousel slide <n> of <total>, vertical 4:5.
Headline text, exactly: "<headline>"
Smaller text, exactly: "<body, max ~15 words>"
Visual: <one concrete picture that explains the idea: an object, a diagram, a scene>.
Text large and readable on a phone. Nothing else written anywhere.
```

**Artwork only (`hybrid` route)**
```
<Style block>
Background artwork for a LinkedIn slide, vertical 4:5, NO TEXT OF ANY KIND.
Subject: <the concrete picture>.
Keep the <top half / left side> calm and empty for a headline to be placed over it.
```

Rules:
- Quote every word that must appear, exactly, and say "nothing else written". Keep on-image text short; long text is where models misspell.
- One idea per image. Describe a concrete thing, not an abstraction ("a stack of unpaid invoices on a desk", not "financial stress").
- No real people's faces or names, no other companies' logos, no copyrighted characters.
- Put the author's name, logo and page numbers in the HTML overlay, not in the model prompt.

## Keys and money

- Keys belong to the owner, live only on their computer, and are never printed, logged, committed or pasted into chat. `visuals.py keys init` creates the file (`~/.bbm-agents.env`); the owner opens it and pastes the key themselves. On Windows it's in their user folder (`C:\Users\<them>\.bbm-agents.env`).
- Fal key: fal.ai → Dashboard → Keys. Higgsfield: console.higgsfield.ai → API keys (a key ID and a secret).
- **Before any paid run:** tell the owner the provider, the model, how many images, and where to check the price. Wait for a yes. Run `--dry-run` first on anything over a few images. The script refuses more than 12 images per run unless `--max` is raised after the owner agrees to the count.
- Regenerate only the slides that failed the check, never the whole set.
