# Blueprint format

The plan as JSON, so `gads.py blueprint check` can catch mistakes and `blueprint render` can print the build sheet, and so `google-ads-audit --blueprint` can later compare the live account with the plan.

Keywords use Google's own notation as strings: `"[exact]"`, `"\"phrase\""` (quoted), `broad` (bare). An object `{"text": "...", "match": "EXACT"}` also works. Money is in the account currency.

```json
{
  "business": "Acme Roofing",
  "customer_id": "1234567890",
  "created": "2026-10-01",
  "currency": "USD",
  "goal": "leads",
  "brand_terms": ["acme roofing", "acme roofs"],

  "economics": {
    "average_sale": 9000,
    "close_rate": 0.25,
    "break_even_cpa": 2250,
    "target_cpa": 300,
    "monthly_budget": 3000,
    "assumptions": ["Close rate is the owner's estimate", "6% conversion rate assumed until 30 days of data"]
  },

  "conversions": {
    "primary": [
      {"name": "Quote form submit", "category": "SUBMIT_LEAD_FORM", "counting": "ONE", "value": 2250,
       "how": "Google tag event on the thank-you page, enhanced conversions on"},
      {"name": "Calls from ads 60s+", "category": "PHONE_CALL_LEAD", "counting": "ONE", "value": 2250,
       "how": "Call asset with Google forwarding number, 60 second minimum"}
    ],
    "secondary": [
      {"name": "Phone number clicks on site", "how": "Google tag click event"}
    ]
  },

  "geo": {"type": "PRESENCE", "locations": ["Denver, CO (<id from gads.py geo>)", "Aurora, CO (<id from gads.py geo>)"], "exclude": []},
  "schedule": "Mon-Fri 7am-6pm, Sat 8am-12pm (when calls are answered)",

  "negatives": {
    "account": ["jobs", "careers", "salary", "\"how to\"", "diy", "[acme roofing]"]
  },

  "campaigns": [
    {
      "name": "Search | Brand",
      "type": "SEARCH",
      "budget_daily": 5,
      "bidding": "MAXIMIZE_CLICKS",
      "networks": {"search_partners": false, "display": false},
      "why": "Protects people searching our name; cheap clicks.",
      "ad_groups": [
        {
          "name": "Brand",
          "landing_page": "https://acme.example/",
          "keywords": ["[acme roofing]", "\"acme roofing\"", "[acme roofs]"],
          "ads": [{"headlines": ["..."], "descriptions": ["..."], "path1": "roofing", "path2": "denver"}]
        }
      ]
    },
    {
      "name": "Search | Roof Repair | Denver",
      "type": "SEARCH",
      "budget_daily": 90,
      "bidding": "MAXIMIZE_CONVERSIONS",
      "target_cpa": null,
      "expected_conversions_month": 18,
      "networks": {"search_partners": false, "display": false},
      "negatives": ["\"acme\""],
      "why": "Highest-intent service with real volume; one campaign so bidding gets all the data.",
      "ad_groups": [
        {
          "name": "Roof repair",
          "landing_page": "https://acme.example/roof-repair",
          "keywords": ["\"roof repair\"", "[roof repair denver]", "\"roof leak repair\"", "[roofer near me]"],
          "negatives": [],
          "ads": [
            {
              "headlines": ["Roof Repair in Denver", "Leaks Fixed This Week", "..."],
              "descriptions": ["...", "...", "...", "..."],
              "path1": "roof-repair",
              "path2": "denver"
            }
          ]
        }
      ]
    }
  ],

  "assets": {
    "sitelinks": [
      {"text": "Free Roof Inspection", "desc1": "Owner inspects every roof", "desc2": "Photos and a written quote", "url": "https://acme.example/inspection"}
    ],
    "callouts": ["Licensed and Insured", "Free Estimates", "Family Owned", "Same Week Repairs"],
    "snippets": [{"header": "Services", "values": ["Roof Repair", "Roof Replacement", "Gutters", "Inspections"]}],
    "call": "+1 303 555 0100"
  },

  "phases": [
    "Month 2: add Roof Replacement campaign if repair hits 15+ conversions/month",
    "Month 3: target CPA once 30+ conversions/month"
  ]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `business`, `goal`, `campaigns` | yes | goal: `leads`, `sales`, `calls`, `store_visits` or `awareness` |
| `customer_id` | if an account exists | 10 digits |
| `brand_terms` | recommended | lets the check and the audit tell brand from non-brand |
| `economics` | recommended | `monthly_budget` is compared with the sum of daily budgets; label `assumptions` |
| `conversions.primary` | yes | 1-3 real outcomes; `category` uses Google's names (SUBMIT_LEAD_FORM, PHONE_CALL_LEAD, BOOK_APPOINTMENT, PURCHASE, REQUEST_QUOTE, CONTACT...) |
| `geo.locations` | yes | names with the IDs from `gads.py geo`; `type` should be PRESENCE |
| `campaigns[].type` | yes | SEARCH, PERFORMANCE_MAX, SHOPPING, DISPLAY, DEMAND_GEN, VIDEO |
| `campaigns[].bidding` | yes | MAXIMIZE_CLICKS, MANUAL_CPC, MAXIMIZE_CONVERSIONS, TARGET_CPA, MAXIMIZE_CONVERSION_VALUE, TARGET_ROAS |
| `campaigns[].expected_conversions_month` | recommended | from `gads.py budget`; the check warns when a target strategy has too little data |
| `ad_groups[].landing_page` | yes | a real page; the homepage only for brand |
| `ad_groups[].ads[]` | yes for Search | headlines 3-15 (aim 10-15), descriptions 2-4 (aim 4) |

What `blueprint check` enforces: character limits, headline and description counts, duplicate headlines, em dashes, exclamation marks in headlines, excessive capitals, keywords missing or duplicated across ad groups, negatives that block your own keywords, broad match without smart bidding, Display or Search Partners on Search campaigns, micro-events as primary conversions, missing locations, presence-or-interest, missing budgets or landing pages, brand not excluded from non-brand campaigns, fewer than 4 sitelinks or callouts, snippets with fewer than 3 values, no call asset for lead businesses, and campaign budgets that don't add up to the monthly budget.
