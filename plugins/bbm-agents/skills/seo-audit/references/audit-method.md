# Audit method: checklists and thresholds

Reference for `seo-audit` (and `seo-page`, `seo-local`, which reuse parts). Numbers are the working thresholds; where a number is a convention rather than a Google rule, it says so.

## On-page

- **Title**: present, unique per page, 30-60 characters (aim 50-60; Google cuts by pixel width, so this is a proxy). Main keyword near the front, brand at the end. Bad: "Home", repeated keywords.
- **Meta description**: present, unique, 120-160 characters, specific to the page, ends on a real reason to click. Flag descriptions that just repeat the title, and the same stock ending ("Learn more today!") across many pages.
- **H1**: exactly one, matches what the page is for, includes the main keyword. Flag H1/H2 text that is only a number or 1-3 characters (counter widgets).
- **Headings**: logical order, no skipped levels (H2 then H4).
- **URL**: short, lowercase, hyphens, no parameters. Flag over 100 characters.
- **Canonical**: present, self-referencing unless the page is a deliberate copy.
- **Meta robots**: index, follow unless intentional. Any `noindex` on a page that should rank is Critical.
- **Open Graph**: og:title, og:description, og:image (1200x630). Low priority, but shared links look broken without og:image.
- **Keyword placement** (for the page's one main keyword): title, H1, URL, meta description, first 100 words, one image alt. Not needed in every H2. No density target; more than about 3% reads as stuffing.
- **Internal links**: descriptive anchor text (never "click here"); every page linked from somewhere; key pages within 3 clicks of the homepage.

## Technical

- **robots.txt**: exists and doesn't block important pages, CSS or JS. A **5xx on robots.txt** makes Google treat the whole site as off-limits: Critical. A 404 means "no restrictions": fine.
- **Sitemap**: listed in robots.txt or at `/sitemap.xml`. Valid XML, only real 200 pages, `lastmod` dates that are true (not today's date on every URL).
- **HTTPS**: whole site on HTTPS, `http://` redirects to `https://` in one hop, no `http://` images or scripts on HTTPS pages (mixed content). Missing HTTPS is Critical. Security headers (HSTS, CSP) are good practice, not ranking factors: Low.
- **Redirects**: one hop max; 301 for permanent moves. Chains are Low unless they're on key pages.
- **Soft 404**: a made-up URL must return 404. A 200 means junk URLs can get indexed: Medium.
- **Broken links**: internal links returning 4xx/5xx: High (they waste crawl and frustrate people).
- **JavaScript rendering**: content, title, description, canonical and schema must be in the raw HTML. Under 50 words of raw text on a JS app shell is Critical (most AI crawlers and some search features see an empty page); under 150 words is High.
- **Mobile**: viewport tag present; tap targets at least 24x24px (48x48 is comfortable); same content on mobile and desktop (Google indexes the mobile version).
- **HTML size**: Google reads the first 2 MB of HTML. Flag pages near that (usually inline images or giant inline code).
- There is no manual crawl-rate setting any more; don't recommend one.

## Core Web Vitals

Measured at the 75th percentile of real users (Chrome UX Report). Use field data when PageSpeed Insights has it; lab data is only a guide.

| Metric | Good | Needs improvement | Poor |
|---|---|---|---|
| LCP (largest paint) | 2.5 s or less | 2.5-4.0 s | over 4.0 s |
| INP (response to taps) | 200 ms or less | 200-500 ms | over 500 ms |
| CLS (layout shift) | 0.1 or less | 0.1-0.25 | over 0.25 |

TTFB under 800 ms is good. FID no longer exists (replaced by INP in 2024); never mention it. Speed is a tie-breaker, not a trump card: a slow page with the best answer still beats a fast thin one.

HTML-only hints when there's no measurement: hero image lazy-loaded (LCP), no `fetchpriority="high"` on the hero, scripts in `<head>` without async/defer, images or iframes without width and height (CLS), very large inline scripts (INP).

## Schema (structured data)

- JSON-LD preferred. Every block needs `"@context": "https://schema.org"` and a valid `@type`.
- Use the **most specific type** (`Plumber`, `InsuranceAgency`, `Dentist`, `LegalService`), not bare `LocalBusiness`.
- **No placeholders** (`[Business Name]`, `REPLACE_ME`, `{{...}}`): High.
- Only true facts from the brand folder or the owner. Unknown values stay out, not guessed.
- **Recommend**: Organization, LocalBusiness subtypes, Service, Person (authors), WebSite, BreadcrumbList, BlogPosting/Article, Review/AggregateRating (third-party reviews only), Event, VideoObject, Product/Offer if they sell products.
- **Never recommend**: HowTo (rich result removed 2023); FAQPage for rich results (limited to government and health sites since 2023; an existing FAQPage block is harmless, don't push to remove it); SpecialAnnouncement, CourseInfo, EstimatedSalary, LearningVideo, ClaimReview, VehicleListing (retired 2025).
- **No self-serving review stars**: a business marking up reviews of itself on its own site gets no stars and risks a manual action.
- Schema is not a direct ranking factor. It helps Google understand the page and can earn rich results.

## Images

- Alt text on every meaningful image, 10-125 characters, describing the image (not "image1.jpg", not a keyword list). Decorative images get `alt=""`.
- Width and height (or CSS aspect-ratio) on every image.
- `loading="lazy"` below the fold only. **Never lazy-load the hero.** Before flagging "not lazy-loaded", check for a JS lazy-loader (`data-src`, `data-lazy-src`, class `lazyload`).
- Size targets: thumbnails under 50 KB, content images under 100 KB, hero under 200 KB. Warn at 2x, critical above 500-700 KB.
- WebP or AVIF over JPEG/PNG; SVG for logos and icons.
- Descriptive file names (`roof-repair-denver.webp`, not `IMG_1234.jpg`).

## Content quality and E-E-A-T

Google's own test (Search Central, "Creating helpful content"): **Who** made it (byline, credentials), **How** (first-hand evidence, process, disclosed AI help where a reader would expect it), **Why** (to help people, not to fill a word count). All three weak = at risk.

Internal rubric (Google publishes no numeric weights, only that trust matters most):

| Dimension | Weight | Signals |
|---|---|---|
| Experience | 20 | original photos, real job or client examples with specifics, before/after, process shown |
| Expertise | 25 | named author with credentials, accurate current facts, claims sourced |
| Authoritativeness | 25 | licences, certifications, associations, awards, press, being cited elsewhere |
| Trust | 30 | address, phone, email, privacy policy, HTTPS, reviews, update dates, no deceptive claims |

If Trust is low, cap the whole E-E-A-T score at "weak" regardless of the rest. Bands: 90+ exceptional, 70-89 strong, 50-69 moderate, 30-49 weak, under 30 very low.

Fix order for a weak site: contact details and an About page with real people first; then author bios and first-hand content; then outside mentions and reviews.

**Word-count floors** (to spot thin pages; word count is not a ranking factor, and these are conventions, not Google rules): homepage 500, service page 800, location page 500-600, blog post 1,500, product page 300-400, about page 400. A page well under its floor is probably not covering the topic.

**Location pages**: the swap test. If you can swap the city name and the page still reads fine, it is a doorway page. More than 30 near-identical location pages is a warning; more than 50 needs a real reason.

**Readability** (advisory, not a Google signal): average sentence under 20 words, paragraphs 2-4 sentences, Flesch reading ease 60-70 for a general audience.

**Freshness**: visible dates on articles; update only when something material changes (prices, laws, limits). Changing the date without changing the content is a trust problem.

## Per-fix template

Every recommendation carries: the evidence (what the check saw, where), the exact fix, who does it, and how you'll know it worked (e.g. "URL Inspection in Search Console shows 'Indexed' within 2 weeks").
