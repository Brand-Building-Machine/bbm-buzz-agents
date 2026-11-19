# Proof Elements — Proof Layer

**What this is:** The proof layer. It aggregates every proof-element doctrine into one wireable unit, so an audit can check a page's proof as a whole (or check whether a specific section backs its claims with proof). It is what `proof-check-audit.md` runs against.

## The proof doctrines

Each has its own file in `.brain/sales-page/doctrine/` with principles, examples, and scoring criteria.

**Existing proof doctrines:**
- `written-testimonials.md`
- `testimonials-with-screenshots-or-results.md`
- `before-and-afters.md`
- `video-testimonials.md`

**Newer proof doctrines:**
- `case-studies.md`
- `testimonial-flood.md`
- `strategic-placement-of-testimonials.md` (primarily page-level: where proof sits relative to claims, objections, and features)
- `product-reviews.md`
- `personal-transformation-story.md`
- `studies-research-and-metrics.md`
- `media-placements.md`
- `client-logos-names-and-photos.md`
- `expert-endorsements.md`
- `expert-association.md`
- `expertise-proof.md`

**Scope:** all are page-level and section-level. Run them on the whole page, or on a single section to check whether that section backs its claims with proof (which usually needs whole-page context). Strategic placement and testimonial flood are primarily page-level.

## The core stance: suggest, do not penalize

Many proof elements will not apply to a given page. Not everyone has been featured in the media, has celebrity clients, expert endorsements, or a research team, and that is not a flaw. So:
- **Judge relevance for each proof type.** If the author genuinely does not have it and it does not fit this product, SET IT ASIDE (excluded from the score) and, where useful, SUGGEST how they could build that kind of proof over time (an idea to make the proof stronger), rather than penalizing.
- **Distinguish "missing but relevant" from "not applicable."** A page that badly needs testimonials and has none has a real gap worth flagging. A course author with no celebrity clients is simply not-applicable, so set it aside with a suggestion.
- **Never fabricate proof.** If proof is missing, the fix is to collect real proof or set the element aside, never to invent it.

## Overlap handling (credit once, do not double-penalize)

The proof types overlap heavily: a case study usually contains a testimonial and often a before/after; a personal transformation story overlaps About You and Development Story; a famous client's photo-plus-quote serves client logos AND expert endorsements; a metric can be both studies/metrics and a results testimonial. Credit a shared proof asset under each element it satisfies, and do not double-penalize. One strong proof asset can tick several boxes at once.

## Most proof is visual

Testimonials-as-screenshots, before/afters, videos, star ratings, logos, photos, growth graphs, and study charts cannot be seen from the copy text. So a proof audit must ASK the user which visual proof is actually present before judging (batch the questions). Do not assume visual proof is missing just because it is not in the pasted text.

## Scoring (scope-aware)

- The proof-check audit produces a scope-aware normalized score: only the proof types relevant to this page count toward the denominator; not-applicable types are set aside. This mirrors the light page audit's dynamic scoring, so a page is never punished for lacking proof it could not reasonably have.
- Rate each present proof type strong / moderate / weak against its own doctrine (crediting shared assets once). A missing-but-relevant type counts as a gap; a not-applicable type is set aside with a suggestion. See `proof-check-audit.md` for the procedure and output.
