# Local method: profile questionnaire and citations

## Google Business Profile: the 25 fields

Score each 0 (missing), 1 (present), 2 (present and good), or `"na"` (doesn't apply). Save as JSON with these exact keys, then `seo.py gbp answers.json --industry <industry>`.

```json
{"primary_category": 2, "additional_categories": 1, "business_name": 2, "address": 2, "phone": 2,
 "website": 2, "hours": 1, "verified": 2, "description": 1, "services": 0, "products": "na",
 "photos": 1, "photo_recency": 0, "attributes": 1, "service_areas": 2, "menu_or_services_link": "na",
 "posts": 0, "post_recency": 0, "booking_link": 0, "social_profiles": 1, "logo": 2, "cover_photo": 1,
 "videos": 0, "review_responses": 1, "qa": "na"}
```

**Critical**
| Key | 2 means |
|---|---|
| `primary_category` | the most specific true category |
| `additional_categories` | 3-5 relevant extra categories |
| `business_name` | the real-world name exactly, no added keywords or cities |
| `address` | complete and identical to the website (service-area businesses: hidden, with service area set) |
| `phone` | a local number, identical to the website |
| `website` | links to the right page (homepage, or the location page for multi-location) |
| `hours` | complete, including holiday hours |
| `verified` | verified |

**Important**
| Key | 2 means |
|---|---|
| `description` | 250-750 characters, what/who/where, natural language |
| `services` | every service listed, each with a short description |
| `products` | products with prices where they sell products (else `"na"`) |
| `photos` | 10+ real photos: logo, cover, exterior, interior, team, work |
| `photo_recency` | a new photo in the last 30 days |
| `attributes` | all true attributes set |
| `service_areas` | set, up to 20 areas (service-area businesses; storefronts `"na"`) |
| `menu_or_services_link` | menu or services link set where the category offers it |

**Supplementary**
| Key | 2 means |
|---|---|
| `posts` | posting about weekly |
| `post_recency` | a post in the last 7 days |
| `booking_link` | booking or appointment link set |
| `social_profiles` | social profiles linked |
| `logo` | logo uploaded |
| `cover_photo` | a good cover photo |
| `videos` | at least one video |
| `review_responses` | replies to 80%+ of reviews |
| `qa` | questions answered, if the listing still shows Q&A; otherwise `"na"` and check the website FAQ |

Industry weighting (`--industry`): `professional` doubles services, 1.5x description, halves photos; `legal` the same; `healthcare` doubles services, 1.5x hours and attributes; `home_services` doubles service areas, 1.5x hours and photos; `restaurant` doubles menu, 1.5x photos, booking, attributes; `real_estate` doubles photos, 1.5x social and posts; `automotive` doubles products and photos, 1.5x services.

Bands: 90+ excellent, 75-89 good, 50-74 needs work, 25-49 poor, under 25 critical.

## Citations

Check name, address and phone on each; the same everywhere is what matters.

**Tier 1 (every local business)**: Google Business Profile, Apple Business Connect (Apple Maps, Siri), Bing Places (Bing, Copilot, and assistants that use Bing's data), Facebook, Yelp.

**Tier 2**: BBB, Nextdoor, Foursquare, YellowPages, Manta.

**Data aggregators** (feed many smaller sites): Data Axle, Foursquare, Neustar Localeze.

**Industry directories**
- Insurance and employee benefits: the state insurance department's licence lookup (make sure the licence record matches), NIPR producer lookup, carrier "find a broker" directories the owner is appointed with, NABIP member directory, local chamber of commerce.
- Accountants and financial: CPA society directory, NAPFA or similar, local chamber.
- Legal: state bar directory, Avvo, Justia, FindLaw, Martindale-Hubbell.
- Healthcare: Healthgrades, Zocdoc, WebMD, Vitals, the NPI registry, state licensing board.
- Home services: Nextdoor, BBB, Thumbtack, Angi, Houzz, manufacturer "find a pro" programs.
- Real estate: Zillow, Realtor.com, Homes.com, Redfin.
- Automotive: Cars.com, CarGurus, DealerRater, Edmunds.
- Restaurants: Yelp, TripAdvisor, OpenTable, delivery apps.

Don't quote "domain authority" numbers for directories; they're vendor metrics.

## Local schema, what good looks like

```json
{
  "@context": "https://schema.org",
  "@type": "InsuranceAgency",
  "@id": "https://example.com/#business",
  "name": "Exact Business Name",
  "url": "https://example.com/",
  "telephone": "+1-406-555-0100",
  "address": {"@type": "PostalAddress", "streetAddress": "12 Main St, Ste 4",
              "addressLocality": "Bozeman", "addressRegion": "MT", "postalCode": "59715", "addressCountry": "US"},
  "geo": {"@type": "GeoCoordinates", "latitude": 45.67970, "longitude": -111.03850},
  "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "08:00", "closes": "17:00"}],
  "areaServed": [{"@type": "City", "name": "Bozeman"}, {"@type": "City", "name": "Belgrade"}],
  "sameAs": ["<Google profile URL>", "<Facebook URL>", "<LinkedIn URL>", "<Yelp URL>"]
}
```

Every value above is illustrative; fill only from the brand folder and the owner. Service-area businesses that hide their street address on Google: keep `addressLocality`, `addressRegion`, `postalCode` and drop `streetAddress`. Multi-location: one block per location page, each with its own `@id` and `"parentOrganization": {"@id": "https://example.com/#org"}`. Each service page can carry a `Service` block with `"provider": {"@id": "https://example.com/#business"}`.

Useful specific types: `InsuranceAgency`, `FinancialService`, `AccountingService`, `LegalService` (not `Attorney`), `Plumber`, `Electrician`, `HVACBusiness`, `RoofingContractor`, `GeneralContractor`, `HousePainter`, `Locksmith`, `MovingCompany`, `Dentist`, `MedicalClinic`, `Physician`, `RealEstateAgent`, `AutoRepair`, `BeautySalon`, `DaySpa`, `ChildCare`, `EmploymentAgency`, `TravelAgency`, `Restaurant`.
