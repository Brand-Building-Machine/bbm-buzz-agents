# Deep Editing — Craft Layer

**What this is:** The deep editing layer. It is the full set of craft/editing checks a deep audit applies on top of a section's (or a page's) own doctrine. It aggregates the ten editing doctrines into one wireable unit, so an audit can invoke "the deep editing layer" as a whole. It is richer and more thorough than `lean-editing.md`.

**Relationship to `lean-editing.md` (both are kept):** `lean-editing.md` is the quick 8-point craft lens for fast, light audits (used by `light-sales-page-audit.md`). This deep editing layer is the full craft layer for deep audits (a deep single-section audit, or a full-page editing audit). They do not conflict; lean-editing is essentially a fast subset of what this covers. Use lean-editing when speed matters, and this layer when depth matters.

## The ten editing doctrines

Each has its own file in `.brain/sales-page/doctrine/` with principles, examples, and scoring criteria.

**Section-level editing doctrines** — apply to a single section, and also across the whole page:
- `clarity.md`
- `writing-tone.md`
- `language-of-the-audience.md`
- `show-dont-tell.md`
- `powerful-language.md`
- `tightening-up.md`
- `emotion.md` (the per-section checks only: one clear core emotion, made specific, made tangible)

**Page-level editing doctrines** — apply only across the whole page (they need the whole page to judge):
- `flow.md`
- `hook-points.md`
- `subheadings.md`
- `emotion.md` (the page-level checks: the emotional roller-coaster, and ending on a positive note)

## How to apply it

**In a deep single-section audit:** run the SECTION-LEVEL editing doctrines' criteria on that section, in addition to the section's own doctrine. Fold everything into ONE combined assessment and one combined score, exactly as an audit already does with lean-editing: judged by the same MET/PARTIAL/MISSING logic, woven into one unified report, never signalling which doctrine each criterion came from. Do NOT run the page-level editing doctrines (flow, hook points, subheadings, the roller-coaster) on a single section, since they need the whole page.

**In a full-page editing audit:** run ALL editing doctrines. The section-level ones are applied across the whole page (is the copy clear, vivid, tight, on-voice, in the audience's language, emotional throughout), and the page-level ones judge the page as a whole (flow, hook points, subheadings, the roller-coaster, the ending). See `.brain/sales-page/deep-audit.md`.

## Overlap handling (credit once, do not double-penalize)

These doctrines overlap each other by design: powerful language, show don't tell, and emotion all touch vivid and tangible language; writing tone and clarity both touch plain, personal wording; subheadings and hook points both touch curiosity. When the same strength or weakness shows up under more than one check, note it once and do not stack several penalties onto one underlying issue. The goal is one honest read of the copy's craft, not a pile-up.

## Scoring

- Judge each criterion MET / PARTIAL / MISSING / set-aside by the same rules as any audit (see the audit skill's judging scale). Set a criterion aside only where it genuinely does not apply (for example, show don't tell's data-visual check on a page that cites no data, or the audience-language check on a short functional line).
- In a deep single-section audit, these section-level editing criteria join the section's own criteria in ONE combined pool, which feeds the section's band and Copy Score (see the audit engine's scoring).
- In a full-page editing audit, produce a normalized editing score plus a per-element read (see `.brain/sales-page/deep-audit.md`).
