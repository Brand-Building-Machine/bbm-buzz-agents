# The edit pass

Run this on every draft before the owner sees it, including drafts the owner wrote. It removes what readers (and LinkedIn's "AI slop" report button) react to. It does not try to beat AI detectors; nothing reliably does, and saying otherwise would be a lie.

Method adapted from the humanizer in sergebulaev/linkedin-skills (MIT).

## 1. Scrub

Judge by the **paragraph**, not the word. One odd word is fine. Three in one paragraph means rewrite the paragraph.

- **Model leakage** (always remove): "As an AI", "as of my last update", `[Your Name]`, `{{PLACEHOLDER}}`, citation tokens.
- **Tell words at density:** significant, crucial, notably, comprehensive, insights, robust, leverage, foster, landscape, nuanced, holistic, streamline, elevate, empower, seamless, unlock, harness, navigate, journey, game-changer, transformative, pivotal.
- **Reveal bridges and teasers** (remove every one): "The result?", "Plot twist:", "Here's the thing", "Let that sink in", "what nobody tells you", "what most people miss", "the real question is".
- **Stock frames** (at most one per post, usually zero): "It's not X, it's Y", "Stop X. Start Y.", "No X. No Y. Just Z."
- **Sincerity announcements** (remove the frame, keep the fact): "let me be honest", "I'll be real", "real talk", "confession:", "unpopular opinion".
- **Punctuation:** no em dashes (use a comma, colon, full stop or parentheses). No `--` or spaced en dashes between clauses.
- **Bait closers:** "What do you think?", "Agree?", "Tag someone who...", "Comment YES and I'll send it". Replace with a specific question or a clean last line.

## 2. Rhythm

- Fix a paragraph only if every sentence runs the same length and reads flat; then change one sentence.
- **Never manufacture punchiness.** Runs of fragments ("Simple. Fast. Done."), one-word paragraphs, and "Why? Because..." are now the loudest tell. Two short fragments in a whole post is plenty.
- Keep the layout: short paragraphs with blank lines are fine.

## 3. Add what only a human has

Each post needs at least:
- One exact number **with its referent** ("$4,730 of rework on one job in March", not "thousands").
- One named thing: a person (with permission), a place, a date, a tool, a customer type.
- One concrete moment: what they saw, heard, or did.

Take these from the story bank or the owner. **Never invent them.** If the draft needs one and there isn't one, ask the owner a single specific question ("What did that mistake cost, roughly, and when?") or leave `[Client to provide]`.

Do not add hedges ("perhaps", "I might be wrong") or confessional framing the owner didn't write. Performed humility reads as AI.

## 4. Check the edit didn't overdo it

Re-read once:
- Did the edit create fragment runs or a short/long/short seesaw? Merge them back.
- Did it add a frame or hedge the owner never wrote? Remove it.
- Did it sand off the owner's voice (their phrases, their quirks, their one natural list of three, every long sentence chopped)? Put it back.

A clean draft gets two or three touches, not a rewrite. When unsure whether something is the owner's voice or the model's, leave it.

## 5. Run the checker

`linkedin.py lint <file>` must report no errors. Treat each warning as a question: fix it, or keep it on purpose and be able to say why.
