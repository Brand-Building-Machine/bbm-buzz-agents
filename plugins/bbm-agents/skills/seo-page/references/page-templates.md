# Page templates

Section plans by page type. Adapt to the business; drop any section it can't honestly fill. Lengths are planning ranges, not targets.

## Service page (about 800-1,500 words)

| Section | Purpose | Format |
|---|---|---|
| H1: <Service> in <City/Area> (or <Service> for <Who>) | match the search | one line |
| Opening | what it is, who it's for, the main result, the next step | 2-3 short sentences; keyword in the first 100 words |
| Who needs it | the situations that make people search | 4-6 bullets in the customer's words |
| How it works | the real process | numbered steps, 3-6 |
| Cost / how pricing works | the question everyone has | a range or table from `offers.md`; if they can't publish prices, explain what drives the price |
| What you get / results | proof | specifics from the brand folder: numbers, a short real example, credentials |
| Why us | the differentiators | 3-5 specific bullets, no clichés |
| FAQ | real objections | 4-8 questions from sales calls, 40-60 word answers |
| CTA | one clear next step | button text + one line; phone for local |

Schema: `Service` (provider = the business `@id`) + the LocalBusiness block on the site.

## Location page (about 500-900 words, genuinely local)

| Section | Format |
|---|---|
| H1: <Service> in <City> | one line |
| What we do in <City> | 2-3 sentences with real local detail |
| Areas served | list of neighborhoods/towns, or a map |
| Local proof | jobs or clients there, a local review or two that mention the place |
| Team in <City> | who, if there is a local team or office |
| Local FAQs | 3-5 questions specific to that area (permits, weather, state rules, drive time) |
| CTA | local phone, address or booking |

Must pass the swap test: if you can replace the city name and it still reads fine, it's a doorway page. Rewrite it or don't publish it. Schema: LocalBusiness subtype with that location's address, phone, geo.

## Landing page (for an offer or campaign)

Hero (offer + one CTA) / the problem in 2-3 sentences / 3-5 benefits / proof (reviews, results, logos) / how it works in 3 steps / 4-6 objections answered / final CTA. One conversion goal. Schema: WebPage.

## Hub page (services overview, a category)

Scope in 2-3 sentences / one H2 or H3 per child page with a two-line summary and a link (every child page that exists, no invented ones) / who we help / how we work / FAQ / CTA. Schema: `Service` or `ItemList` + `BreadcrumbList`.

## Homepage

Hero: what you do, for whom, where, and a CTA / services grid linking to each service page / 3-5 differentiators / proof / service area or location / 4-6 broad FAQs / CTA. Keyword: main service + place. Schema: Organization + WebSite (+ LocalBusiness for local businesses).

## About page

Who we are / the founding story with real dates / team with credentials and photos / values in practice (not a word list) / licences, awards, memberships with dates / press mentions / CTA. Schema: Organization + `Person` for each named team member.

## FAQ page

8-15 real questions, grouped by topic, 40-60 word answers that link to the relevant service page. Schema: WebPage (FAQPage earns no rich result for most businesses; fine to add, don't promise anything).

## Case study

Result first (one line with the number) / the situation / the challenge / what we did / the result with figures / 3-5 takeaways / related service CTA. Only real cases the owner supplies, with the client's permission. Schema: Article.

## Title and meta description

- Title: 50-60 characters (30-60 hard bounds), keyword first, specifics over adjectives, brand last with the site's usual separator.
- Meta description: about 150 characters (120-160), active voice, adds something the title didn't (a USP, the area, a proof point), ends with the next step. Avoid unescaped double quotes.

## Internal links

3-5 links out to related pages with descriptive anchors (2-6 words, never "click here" or "learn more"). List the 2-3 existing pages that should link **to** the new page, with the sentence and anchor to add, for the owner's approval.
