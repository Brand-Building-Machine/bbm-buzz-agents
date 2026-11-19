# Skill: proof-check-audit

*Amended 2026-11-04, v2 batch 1: any piece of copy (V2-2), visual proof read from the page and never asked about before scoring (V2-18), the workspace pointers and paths replaced (V2-22, V2-23).*

Purpose: audit a whole piece of copy against ALL proof elements at once. It maps what proof the page has, rates how strong each is, flags the proof it is genuinely missing, and, for the proof types that do not apply, suggests ideas to make the proof stronger over time. It ends with a scope-aware proof score and a prioritized list.

Invoke: "run proof check audit" (or "proof-audit this page"), then I'll paste the copy or give the link.

**Where this file says "page", read "the piece being audited".**

This skill ASSESSES and SUGGESTS. It does not write or rewrite copy. It never fabricates proof; where proof is missing, the fix is to collect real proof, not invent it.

## The stance: suggest, don't penalize

Many proof types will not apply to a given page. Not everyone has been in the media, has celebrity clients, expert endorsements, or a research team, and that is not a flaw. So a not-applicable proof type is set aside (excluded from the score) with a short idea for how they could build it over time, rather than counted against them. Only proof that is genuinely relevant-and-missing counts as a gap. (See `resources/proof-elements.md`.)

## Steps

1. **Load the proof layer.** Read `resources/proof-elements.md` and the proof doctrines it lists (the existing four plus the newer eleven). Also read `resources/coach-voice.md` and follow it for the voice of everything you write; reread your draft against its never-say list before sending.
2. **Read the page** I give you.
3. **Map the proof, and judge relevance for each type** (proof-elements.md's stance):
   - **Present** — the page uses this proof type. Band it strong / moderate / weak against its doctrine.
   - **Missing but relevant** — the page should have this and does not (for example, no testimonials at all on a page that badly needs them). A real gap; counts against the score.
   - **Not applicable** — the author genuinely could not reasonably have this (celebrity clients, media features, a research team). Set aside, excluded from the score, with a one-line idea for how they could build it.
   - Watch the overlaps and credit shared assets once (a case study that contains a testimonial and a before/after; a personal transformation story that overlaps About You). Do not double-penalize.
4. **★ Read the visual proof; never ask before scoring.** Testimonial screenshots, before/afters, star ratings, logos, results graphics and charts are read from the page's images (SKILL.md's read). Proof that still could not be read is never counted missing: it is judged on what is visible and named in the "couldn't read" line. If the user supplies it, recompute.
5. **Band every present proof type** strong / moderate / weak (definitions below), against its own doctrine.
6. **Compute the scope-aware proof score** (below) and write the report (format below).

## The bands

- **🟢 Strong** — this proof type is present and done well (specific, believable, well-placed, visual where it should be). Hard to argue with.
- **🟡 Moderate** — present and helping, with real gaps (vague results, no numbers, buried, no visual where one would help).
- **🔴 Weak** — present but doing little (generic praise, unproven claims, "complete but hollow" proof).
- **❌ Missing (relevant)** — a proof type the page genuinely needs and lacks. A gap.
- **➖ Not applicable** — set aside with a suggestion. The author could not reasonably have this yet; excluded from the score.

When torn between two bands, choose the lower one.

## The proof score (scope-aware)

Give one proof score out of 100, counting only the proof types that are in scope for this page.

Map each in-scope proof type to points:
- 🟢 Strong = 1.0
- 🟡 Moderate = 0.6
- 🔴 Weak = 0.3
- ❌ Missing (relevant) = 0.0
- ➖ Not applicable = excluded from the calculation entirely

**In-scope** = every present proof type plus every missing-but-relevant one. Not-applicable types are excluded.

**Proof score** = ( sum of points across in-scope proof types ÷ number of in-scope proof types ) × 100, rounded.

State in one line what the number reflects (for example: "Proof score: 58/100. This counts only the proof this page should have; the kinds you couldn't reasonably have yet are set aside with ideas below.") Never present it as a ceiling on the copy; it is a picture of this page's proof.

## The report (write it in this order, in the coach voice)

Never use internal doctrine terms or example names to the user; explain in plain words.

**1. Overall read + proof score.** Put the score in the heading (for example "Overall read + proof score: 58/100"). Then a short paragraph: how proof-rich the page is overall, the single biggest proof lever, and the score's one-line meaning.

**2. The proof map.** A scannable list led by band markers: 🟢 / 🟡 / 🔴 for present types, ❌ for relevant gaps, ➖ for not-applicable (each ➖ with its one-line idea). Name any proof you could not read.

**3. Proof by proof.** Go through the present proof types, strongest to weakest. For each: its band, why it lands there in a sentence or a few (more words on the weak ones), and specific ways to strengthen it (be concrete; never fabricate, use placeholders like `[a real client's specific number]`).

**4. Proof worth adding.** The missing-but-relevant proof types: what to add, roughly where on the page, and what a strong version contains. Order by impact.

**5. Ideas to make your proof stronger (the not-applicable set).** For the set-aside types, short, encouraging ideas for building that proof over time (how to earn a media mention, land an expert quote, collect case studies), framed as upside, not obligation.

**6. Priorities.** MUST improve / NICE to have / OPTIONAL, pulling from the weak present types and the relevant gaps. Phrase each as an action.

## Rules

- Follow SKILL.md's standing rules on plain language and product-dependent criteria.
- Assess and suggest only; do not write or rewrite proof. Never fabricate proof (numbers, testimonials, results, media, endorsements).
- Credit a shared proof asset under each element it satisfies; do not double-penalize overlaps.
- The score reflects only in-scope proof. If I later mark a type applicable or not, recompute and show the new number.
- Never ask about proof before scoring; never show a provisional-then-final score.
