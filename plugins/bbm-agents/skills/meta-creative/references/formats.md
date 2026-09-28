# Formats, specs and lead forms

Format ideas adapted from Motion's visual-formats skill (MIT) and coreyhaines31/marketingskills (MIT). Specs are Meta's published recommendations; they change, so when a spec matters, check Meta's Ads Guide.

## 1. Formats that suit service lead gen

Cheap to make, native-looking, proven for local and B2B services. Pick a different one per concept.

| Format | What it is | Make it with |
|---|---|---|
| **Founder / owner to camera** | The owner explains the problem and the offer in 20-45 seconds | A phone, good light, a lav mic |
| **Testimonial** | A real customer's words, video or quote card | Customer (with consent) or a quote card from a 4-5 star review |
| **Review screenshot** | A real Google or Facebook review, big and readable | The review itself (never edited) |
| **Text message / chat** | A realistic thread that tells the story | A screenshot mock-up; clearly illustrative |
| **Notes app / post-it** | A handwritten-feeling list: "3 things to check before renewal" | Phone screenshot or a photo |
| **Checklist / how-to** | Useful content as the ad (trojan horse) | Static carousel or short video |
| **Us vs them** | Two columns: the usual way vs their way | Static, brand colours |
| **Statistic** | One big number with the source | Static; only the owner's or a cited number |
| **Behind the scenes** | The team doing the work | Phone video |
| **Before / after** | Only where honest and allowed: a roof, a garden, a spreadsheet. Never bodies, health or income | Photos from real jobs |
| **Comment reply** | Answer a real question from comments or DMs as the ad | Screenshot of the question plus answer |
| **Expert explainer** | The specialist on one common mistake | Phone video |

Things that look like ads (stock photos, glossy templates, logos first) tend to get scrolled past. Make it look like something a real person posted.

## 2. Specs to brief the designer

| Placement | Aspect ratio | Pixels |
|---|---|---|
| Feed (Facebook, Instagram) | 4:5 (preferred) or 1:1 | 1080 x 1350 / 1080 x 1080 |
| Stories and Reels | 9:16 | 1080 x 1920 |

- Deliver every concept in **4:5 and 9:16** so it fits all placements.
- **9:16 safe zone:** keep text and faces out of roughly the top 14% and bottom 35% (the app's buttons and captions sit there), and away from the side edges.
- The old "20% text" rule is gone. Keep on-image text short enough to read on a phone at a glance (about 7 words).
- Video: the hook lands in the first 2 seconds; captions burned in (most people watch muted); 15-45 seconds for cold traffic.
- Copy: primary text shows about 125 characters before "See more"; headline about 40 characters; description about 30 (often hidden on mobile). `meta.py copy` checks these.

## 3. Instant forms (lead quality lives here)

Meta's in-app forms auto-fill from the profile, so they make it very easy to submit and very easy to forget you did. Friction is how you buy quality:

- **Form type: "Higher intent"** (adds a review screen before submit) unless the owner explicitly wants volume over quality.
- **1-3 qualifying questions**, multiple choice, easiest first. Example for a benefits broker: "How many employees?" (1-9 / 10-49 / 50+), "When is your renewal?" (next 60 days / later / not sure). Four or more questions and completion drops.
- **Ask for what the owner will actually use.** A phone number they'll call beats an email they won't.
- **Intro:** one line restating the offer.
- **Thank-you screen:** exactly what happens next and when ("Sam will call within one business day from a 555 number"). This is the single best fix for leads who don't remember filling in the form.
- **Speed matters more than the form.** Leads contacted within minutes convert far better than next-day. Tell the owner where leads land (Meta Leads Center, or their CRM through an integration) and who calls them.

**Instant form or website?** Instant form when the website is slow, weak or not built for conversion, or for simple offers (quote, callback). Website when the site converts well (roughly 5%+ of visitors), the offer needs explaining, or they need booking in a calendar. A website route needs tracking working first (`meta-tracking`).

## 4. Policy traps for service businesses

- **Personal attributes:** never say or imply what the viewer is (in debt, ill, a certain age, religion, orientation). Talk about situations.
- **Special ad categories:** credit, loans, and other financial products and services (Meta's category covers insurance too; confirm in Ads Manager if unsure), employment, housing, and social issues/elections/politics. These restrict targeting (no age, gender, zip-code or lookalike targeting) and must be declared on the campaign.
- **Before/after and results claims:** no implied health or financial outcomes; no "guaranteed" results unless the business really guarantees them and the brand files say so.
- **Fake UI:** no fake "play" buttons, fake notifications or fake close buttons.
