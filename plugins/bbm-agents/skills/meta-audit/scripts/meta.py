#!/usr/bin/env python3
"""Meta (Facebook + Instagram) lead-gen ads helper. Stdlib only; macOS, Linux, Windows.

Deterministic arithmetic and checks only. Judgement (what it means, what to say) is the agent's job.
Nothing here talks to Meta. Reads come from the Meta ads connector or an Ads Manager export;
writes go through the connector only after the owner approves a plan this script checked.

  meta.py paths [--business NAME]          # where drafts go, where the ads profile lives, brand files present
  meta.py profile init [--business NAME]   # create meta-ads.json next to the brand files (never overwrites)
  meta.py profile check [--business NAME]  # is the profile complete enough to plan changes? exit 1 if not
  meta.py tcpl --cost-per-customer N --lead-to-customer RATE [--daily-budget N]
                                           # target cost per qualified lead + how many ads the budget can feed
  meta.py audit FILE [--tcpl N] [--daily-budget N] [--days N] [--business NAME] [--json]
                                           # FILE = Ads Manager CSV export or JSON rows; kill/keep/scale per row
  meta.py plan FILE [--business NAME] [--json]
                                           # check a change plan (JSON) against the rules + the owner's limits
  meta.py copy FILE [--json]               # lint ad copy (JSON/markdown with primary text, headline, description)
  meta.py log FILE --result verified|failed|unknown [--ids "..."] [--note "..."] [--business NAME]
                                           # append what happened to the launch log

Exit codes: 0 ok, 1 check failed / plan blocked, 2 config or usage problem.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
PROFILE_NAME = "meta-ads.json"
BRAND_FILES = ["brand-bible.md", "voice-agent.md", "offers.md", "root.css"]

# Decision rules. Adapted from the Meta decision system in coreyhaines31/marketingskills (MIT),
# re-expressed for small-business lead gen. Every threshold is a multiple of TCPL.
DATA_GATE_X = 3.0          # judge an ad only after it has spent 3x TCPL
MONITOR_X = 1.5            # cost per qualified lead up to 1.5x TCPL = normal noise
QUAL_SWAP, QUAL_OK = 0.40, 0.60
FAIR_SHARE = 0.5           # at day 7 an ad should have had at least half its even share of spend
EVAL_DAYS = 14             # ad-count ceiling assumes a 14-day read per ad
LEARNING_EVENTS = 50       # results per week Meta wants to exit learning
MAX_STEP_UP = 0.20         # budget increases above +20% in one move get flagged
FREQ_BANDS = {"cold": (2.5, 4.0), "warm": (4.0, 6.0)}   # (warning from, critical above)

# Meta's recommended visible lengths. Longer is allowed but gets cut off in the feed.
PRIMARY_VISIBLE, HEADLINE_MAX, DESCRIPTION_MAX = 125, 40, 30

OBJECTIVE_GOAL = {"OUTCOME_LEADS": "LEAD_GENERATION", "OUTCOME_SALES": "OFFSITE_CONVERSIONS",
                  "OUTCOME_TRAFFIC": "LINK_CLICKS", "OUTCOME_ENGAGEMENT": "POST_ENGAGEMENT",
                  "OUTCOME_AWARENESS": "REACH"}
SPECIAL_CATEGORIES = {"none", "financial_products_services", "employment", "housing",
                      "social_issues_elections_politics"}
# EU + EEA: ads reaching them need the beneficiary/payer (DSA) fields.
EU_EEA = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO".split())
BREAKDOWN_COLS = ["placement", "platform", "age", "gender", "region", "country", "impression device",
                  "device platform", "publisher platform", "platform position", "dma region", "time of day"]
WARM_WORDS = ("retarget", "remarket", "warm", "rtg")

# Meta's personal-attributes policy: copy may not assert or imply the viewer's attributes.
PERSONAL_ATTR_RE = re.compile(
    r"\b(are you|do you have|you are|you're|other|fellow)\b[^.?!]{0,40}\b("
    r"in debt|bankrupt|broke|divorced|single|pregnant|depressed|anxious|overweight|fat|diabetic|"
    r"sick|disabled|unemployed|jobless|gay|lesbian|christian|muslim|jewish|black|latino|asian|"
    r"over \d+|under \d+|\d+ or older|a senior|retired|poor|low income|struggling with)\b", re.I)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


# ---------- config ----------

def load_config():
    env = os.environ.get("BUZZ_AGENTS_CONFIG")
    path = Path(env).expanduser() if env else None
    if not path and POINTER.exists():
        try:
            path = Path(json.loads(POINTER.read_text(encoding="utf-8"))["config"]).expanduser()
        except (ValueError, KeyError):
            path = None
    if not path:
        for d in [Path.cwd(), *Path.cwd().parents]:
            if (d / CONFIG_NAME).exists():
                path = d / CONFIG_NAME
                break
    if not path or not path.exists():
        die("No buzz-agents config found. Run the workspace-config skill first.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("PROPOSED_PATH", "BRAND_PATH"):
        if not cfg.get(key):
            die(f"Config has no {key}. Run workspace-config to add it.")
    return cfg


def resolve(pattern, business, what):
    if "{business}" in pattern:
        if not business:
            die(f"This workspace keeps {what} per business. Pass --business <name>.")
        return Path(pattern.replace("{business}", business)).expanduser()
    return Path(pattern).expanduser()


def out_dir(cfg, business):
    base = Path(cfg["PROPOSED_PATH"]).expanduser() / "meta-ads"
    return base / business if business and "{business}" in cfg["BRAND_PATH"] else base


def brand_dir(cfg, business):
    return resolve(cfg["BRAND_PATH"], business, "brand folders")


def load_profile(cfg, business, required=True):
    path = brand_dir(cfg, business) / PROFILE_NAME
    if not path.exists():
        if required:
            die(f"No ads profile at {path}. Run `meta.py profile init` and fill it in with the owner.", 1)
        return None, path
    try:
        return json.loads(path.read_text(encoding="utf-8")), path
    except ValueError as e:
        die(f"{path} is not valid JSON: {e}")


# ---------- numbers ----------

def num(v):
    """Parse '1,234.50', '$12', '3.2%', '' -> float or None. Never guesses."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
    s = s.rstrip("%").strip()
    if s in ("", "-", "--", "—", "n/a", "N/A", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def div(a, b):
    return None if a is None or not b else a / b


def money(v):
    return "n/a" if v is None else f"{v:,.2f}"


def tcpl_from(cost_per_customer, lead_to_customer):
    if cost_per_customer is None or lead_to_customer is None or not (0 < lead_to_customer <= 1):
        return None
    return cost_per_customer * lead_to_customer


def ad_ceiling(daily_budget, tcpl):
    """How many ads the budget can give a fair 14-day read (each needs 2x TCPL)."""
    if not daily_budget or not tcpl:
        return None
    return int(daily_budget * EVAL_DAYS // (2 * tcpl))


# ---------- reading exports ----------

ALIASES = {
    "name": ["ad name", "ad set name", "campaign name", "name"],
    "ad_set": ["ad set name"],
    "campaign": ["campaign name"],
    "status": ["ad delivery", "ad set delivery", "campaign delivery", "delivery", "delivery status", "status"],
    "spend": ["amount spent", "spend", "amount_spent"],
    "leads": ["leads", "meta leads", "on-facebook leads", "website leads", "leads (form)", "results", "lead"],
    "result_type": ["result indicator", "result type"],
    "qualified": ["qualified leads", "qualified", "sql", "qualified_leads"],
    "impressions": ["impressions"],
    "reach": ["reach"],
    "frequency": ["frequency"],
    "link_clicks": ["link clicks", "link_clicks"],
    "start": ["reporting starts", "date start", "date_start", "start"],
    "end": ["reporting ends", "date stop", "date_stop", "end"],
    "daily_budget": ["ad set budget", "campaign budget", "daily budget", "budget"],
}


def norm_key(k):
    k = k.strip().lower().replace("_", " ")
    return re.sub(r"\s*\(.*?\)\s*$", "", k).strip()   # "Amount spent (USD)" -> "amount spent"


def read_rows(path):
    p = Path(path)
    if not p.exists():
        die(f"File not found: {p}")
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data.get("data", data.get("rows", [])) if isinstance(data, dict) else data
        return [dict((str(k), v) for k, v in r.items()) for r in rows]
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def detect_level(keys):
    ks = {norm_key(k) for k in keys}
    if "ad name" in ks:
        return "ad"
    if "ad set name" in ks:
        return "ad set"
    if "campaign name" in ks:
        return "campaign"
    return "row"


def detect_breakdown(keys):
    ks = {norm_key(k) for k in keys}
    return [b for b in BREAKDOWN_COLS if b in ks]


def pick(row, field, level=None):
    wanted = ALIASES[field]
    if field == "name" and level in ("ad", "ad set", "campaign"):
        wanted = [f"{level} name"]
    lowered = {norm_key(k): v for k, v in row.items()}
    for w in wanted:
        if w in lowered and lowered[w] not in (None, ""):
            return lowered[w]
    return None


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(str(s).strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def normalise(raw_rows):
    if not raw_rows:
        return [], "row", []
    keys = list(raw_rows[0].keys())
    level, breakdown = detect_level(keys), detect_breakdown(keys)
    out = []
    for r in raw_rows:
        name = pick(r, "name", level) or pick(r, "name") or "(unnamed)"
        if str(name).strip().lower() in ("total", "totals", "results"):
            continue          # Ads Manager adds a summary row
        rt = (pick(r, "result_type") or "").lower()
        leads = num(pick(r, "leads"))
        cols = {norm_key(k) for k in r}
        only_results = "results" in cols and not (cols & {"leads", "meta leads", "on-facebook leads", "website leads", "lead"})
        leads_note = f"results are '{rt}', not leads" if (rt and "lead" not in rt and only_results) else ""
        out.append({
            "name": str(name).strip(),
            "segment": " / ".join(str(r.get(k) or "") for k in r if norm_key(k) in breakdown) if breakdown else "",
            "campaign": pick(r, "campaign") or "",
            "ad_set": pick(r, "ad_set") or "",
            "status": (pick(r, "status") or "").strip(),
            "spend": num(pick(r, "spend")) or 0.0,
            "leads": leads,
            "leads_note": leads_note,
            "qualified": num(pick(r, "qualified")),
            "impressions": num(pick(r, "impressions")),
            "reach": num(pick(r, "reach")),
            "frequency": num(pick(r, "frequency")),
            "link_clicks": num(pick(r, "link_clicks")),
            "start": parse_date(pick(r, "start")),
            "end": parse_date(pick(r, "end")),
        })
    return out, level, breakdown


# ---------- judging ----------

def freq_flag(row):
    f = row["frequency"]
    if f is None:
        return ""
    kind = "warm" if any(w in (row["name"] + " " + row["campaign"]).lower() for w in WARM_WORDS) else "cold"
    warn, crit = FREQ_BANDS[kind]
    if f > crit:
        return f"frequency {f:.1f} critical for {kind} traffic (> {crit})"
    if f >= warn:
        return f"frequency {f:.1f} in warning band for {kind} traffic ({warn}-{crit})"
    return ""


def judge(row, tcpl, fair_share_min):
    """One verdict per row: wait / kill / swap / monitor / keep / winner, with the reason."""
    spend, leads, q = row["spend"], row["leads"], row["qualified"]
    if row["leads_note"]:
        return "check", row["leads_note"] + "; export the Leads column to judge this row"
    if spend == 0:
        return "kill", "no delivery: Meta spent nothing on it"
    if fair_share_min is not None and spend < fair_share_min:
        return "kill", (f"under-delivered: spent {money(spend)} vs at least {money(fair_share_min)} "
                        "(half an even share of its ad set's spend); Meta deprioritised it")
    if not tcpl:
        return "no-target", "set a target cost per qualified lead (tcpl) to judge this"
    if spend < DATA_GATE_X * tcpl:
        return "wait", f"spent {money(spend)}, under {DATA_GATE_X:g}x target ({money(DATA_GATE_X * tcpl)}); too early"
    if not leads:
        return "swap", f"no leads after {money(spend)} ({spend / tcpl:.1f}x target); drop the concept, don't iterate it"
    if q is not None:
        if q == 0:
            return "swap", "leads but none qualified; keep the format, change the angle"
        rate = q / leads
        if rate < QUAL_SWAP:
            return "swap", f"only {rate:.0%} of leads qualified; the ad attracts the wrong people"
        cost = spend / q
        basis = "qualified lead"
        if rate < QUAL_OK:
            return "monitor", f"{rate:.0%} qualified (40-60%); watch one more week. {money(cost)} per {basis}"
    else:
        cost = spend / leads
        basis = "lead (not qualified: no CRM numbers)"
    if cost <= tcpl:
        return "winner", f"{money(cost)} per {basis}, at or under target {money(tcpl)}"
    if cost <= MONITOR_X * tcpl:
        return "monitor", f"{money(cost)} per {basis}, within 1.5x target; normal noise"
    return "swap", f"{money(cost)} per {basis}, over 1.5x target ({money(MONITOR_X * tcpl)})"


def audit(rows, level, breakdown, tcpl=None, daily_budget=None, days=None):
    if not days:
        starts = [r["start"] for r in rows if r["start"]]
        ends = [r["end"] for r in rows if r["end"]]
        days = (max(ends) - min(starts)).days + 1 if starts and ends else None
    total_spend = sum(r["spend"] for r in rows)
    lead_vals = [r["leads"] for r in rows if r["leads"] is not None]
    total_leads = sum(lead_vals) if lead_vals else None
    q_vals = [r["qualified"] for r in rows if r["qualified"] is not None]
    total_q = sum(q_vals) if q_vals else None

    active = [r for r in rows if r["spend"] > 0 or "active" in r["status"].lower()]
    # Fair share: compare each ad only with the ads it competes with (same ad set, else same campaign),
    # using what that group actually spent. A lone ad in a small retargeting ad set is never "starved".
    groups = {}
    for r in active:
        groups.setdefault((r["campaign"], r["ad_set"]), []).append(r)
    fair_min = {}
    if level == "ad" and not breakdown and days and days >= 7:
        for key, members in groups.items():
            if len(members) >= 2:
                fair_min[key] = sum(m["spend"] for m in members) / len(members) * FAIR_SHARE

    results = []
    for r in rows:
        share = div(r["spend"], total_spend)
        if breakdown:
            verdict, why = "info", "breakdown row: never cut a segment on its average cost alone"
        else:
            verdict, why = judge(r, tcpl, fair_min.get((r["campaign"], r["ad_set"])))
        results.append({**{k: v for k, v in r.items() if k not in ("start", "end")},
                        "cpl": div(r["spend"], r["leads"]),
                        "cost_per_qualified": div(r["spend"], r["qualified"]),
                        "spend_share": share,
                        "fatigue": freq_flag(r),
                        "verdict": verdict, "why": why})

    weekly = (total_leads / days * 7) if (total_leads is not None and days) else None
    ceiling = ad_ceiling(daily_budget, tcpl)
    notes = []
    if weekly is not None:
        if weekly < LEARNING_EVENTS:
            notes.append(f"About {weekly:.0f} leads a week across this export. Meta wants ~{LEARNING_EVENTS} a week "
                         "per ad set to leave learning. Expect 'Learning limited'; that is normal at this budget. "
                         "Fewer ad sets, not more, and judge on 14-day windows.")
        else:
            notes.append(f"About {weekly:.0f} leads a week: enough volume for ad sets to exit learning.")
    if ceiling is not None and level == "ad" and not breakdown:
        n = len(active)
        notes.append(f"The budget can feed about {ceiling} ads for a fair read; {n} are running."
                     + (" Too many: each one starves. Cut before adding." if n > ceiling else ""))
    if breakdown:
        notes.append("Breakdown export (" + ", ".join(breakdown) + "): Meta spends toward the cheapest NEXT lead, "
                     "not the lowest average. A pricier-looking segment is often protecting the whole. "
                     "Report it; never recommend cutting a segment on this alone.")
    if total_q is None and total_leads:
        notes.append("No qualified-lead numbers. Verdicts use raw leads. Ask the owner how many leads per ad "
                     "turned into real prospects; that is the number that matters.")
    return {
        "level": level, "breakdown": breakdown, "days": days, "rows": results,
        "totals": {"spend": total_spend, "leads": total_leads, "qualified": total_q,
                   "cpl": div(total_spend, total_leads), "cost_per_qualified": div(total_spend, total_q),
                   "leads_per_week": weekly},
        "tcpl": tcpl, "daily_budget": daily_budget, "ad_ceiling": ceiling, "notes": notes,
    }


def print_audit(a):
    t = a["totals"]
    print(f"Level: {a['level']}" + (f" (breakdown: {', '.join(a['breakdown'])})" if a["breakdown"] else ""))
    print(f"Window: {a['days'] or '?'} days | Spend {money(t['spend'])} | Leads {format(t['leads'], 'g') if t['leads'] is not None else 'n/a'}"
          f" | CPL {money(t['cpl'])}" + (f" | Qualified {t['qualified']:g} ({money(t['cost_per_qualified'])} each)"
                                         if t["qualified"] is not None else ""))
    print(f"Target cost per qualified lead: {money(a['tcpl']) if a['tcpl'] else 'not set'}"
          + (f" | Ad ceiling: {a['ad_ceiling']}" if a["ad_ceiling"] is not None else ""))
    print()
    order = {"kill": 0, "swap": 1, "check": 2, "monitor": 3, "wait": 4, "winner": 5, "no-target": 6, "info": 7}
    for r in sorted(a["rows"], key=lambda r: (order.get(r["verdict"], 9), -r["spend"])):
        label = r["name"] + (f" [{r['segment']}]" if r["segment"] else "")
        leads = "n/a" if r["leads"] is None else f"{r['leads']:g}"
        share = "" if r["spend_share"] is None else f" ({r['spend_share']:.0%} of spend)"
        print(f"{r['verdict'].upper():8} {label}")
        print(f"         spend {money(r['spend'])}{share} | leads {leads} | CPL {money(r['cpl'])}"
              + (f" | freq {r['frequency']:.1f}" if r["frequency"] is not None else ""))
        print(f"         {r['why']}")
        if r["fatigue"]:
            print(f"         fatigue: {r['fatigue']}")
    if a["notes"]:
        print("\nNotes:")
        for n in a["notes"]:
            print(f"- {n}")


# ---------- copy lint ----------

def lint_copy(ad):
    """Return a list of (severity, message) for one ad's copy."""
    issues = []
    primary = (ad.get("primary_text") or "").strip()
    headline = (ad.get("headline") or "").strip()
    desc = (ad.get("description") or "").strip()
    if not primary:
        issues.append(("error", "no primary text"))
    first = primary.split("\n", 1)[0]
    if len(primary) > PRIMARY_VISIBLE and len(first) > PRIMARY_VISIBLE:
        issues.append(("warn", f"hook runs past the first {PRIMARY_VISIBLE} characters; it gets cut off at 'See more'"))
    if headline and len(headline) > HEADLINE_MAX:
        issues.append(("warn", f"headline is {len(headline)} characters; over {HEADLINE_MAX} gets truncated"))
    if desc and len(desc) > DESCRIPTION_MAX:
        issues.append(("warn", f"description is {len(desc)} characters; over {DESCRIPTION_MAX} gets truncated"))
    for label, text in (("primary text", primary), ("headline", headline), ("description", desc)):
        if "—" in text:
            issues.append(("error", f"em dash in {label}; use a comma, period or colon"))
        if PERSONAL_ATTR_RE.search(text):
            issues.append(("warn", f"{label} may imply the viewer's personal attributes "
                                    f"('{PERSONAL_ATTR_RE.search(text).group(0)}'); Meta rejects these. "
                                    "Talk about the situation, not the person"))
        letters = [c for c in text if c.isalpha()]
        if len(letters) > 12 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
            issues.append(("warn", f"{label} is mostly capitals; reads as shouting and can be rejected"))
        if text.count("!") > 2:
            issues.append(("warn", f"{label} has {text.count('!')} exclamation marks"))
        if re.search(r"\[.*?(client to provide|tbd|todo|placeholder).*?\]", text, re.I):
            issues.append(("error", f"{label} still has a placeholder"))
    if re.match(r"^(introducing|discover|are you looking for)\b", primary, re.I):
        issues.append(("warn", "opens like an ad ('Introducing', 'Discover', 'Are you looking for'); lead with the pain"))
    return issues


def load_ads(path):
    p = Path(path)
    if not p.exists():
        die(f"File not found: {p}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        return data.get("ads", data) if isinstance(data, dict) else data
    # markdown: blocks under "## <name>" with lines "Primary text:", "Headline:", "Description:"
    ads, cur, field = [], None, None
    for line in text.splitlines():
        m = re.match(r"^#{2,3}\s+(.+)", line)
        if m:
            cur = {"name": m.group(1).strip(), "primary_text": "", "headline": "", "description": ""}
            ads.append(cur)
            field = None
            continue
        if cur is None:
            continue
        m = re.match(r"^\*{0,2}(primary text|headline|description)\*{0,2}\s*:\s*\*{0,2}\s*(.*)$", line.strip(), re.I)
        if m:
            field = m.group(1).lower().replace(" ", "_")
            cur[field] = m.group(2).strip()
        elif field == "primary_text" and line.strip() and not re.match(r"^\*{0,2}[A-Z][\w ]+:\s", line.strip()):
            cur[field] += "\n" + line.strip()
        elif re.match(r"^\*{0,2}[A-Z][\w ]+:\s", line.strip()):
            field = None
    return [a for a in ads if any(a.get(k) for k in ("primary_text", "headline", "description"))]


# ---------- plans ----------

def plan_id(plan):
    body = json.dumps(plan, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]


def check_plan(plan, profile):
    """Return (blocks, warnings, risks). Any block = do not ask the owner to approve yet."""
    blocks, warns, risks = [], [], []
    action = plan.get("action")
    if action not in ("create", "update", "pause", "activate"):
        blocks.append("action must be one of create, update, pause, activate (deleting is never offered)")
        return blocks, warns, risks

    prof = profile or {}
    ceiling_budget = num(prof.get("max_daily_budget"))
    acct = str(plan.get("account_id") or "")
    if not re.match(r"^(act_)?\d{5,}$", acct):
        blocks.append("account_id missing or not an ad account id (act_ + digits); read it from the connector")
    elif prof.get("ad_account_id") and acct.replace("act_", "") != str(prof["ad_account_id"]).replace("act_", ""):
        blocks.append(f"account_id {acct} is not the account in the owner's profile ({prof['ad_account_id']})")

    if action == "activate":
        risks.append("STARTS SPENDING: turns delivery on")
        if not plan.get("targets"):
            blocks.append("activate needs `targets`: the exact ids to turn on")
        if ceiling_budget is None:
            blocks.append("owner has no max_daily_budget in their ads profile; no spend without a ceiling")
        return blocks, warns, risks

    if action == "pause":
        risks.append("STOPS DELIVERY on the listed targets (reversible: turn back on)")
        if not plan.get("targets"):
            blocks.append("pause needs `targets`: the exact ids to pause")
        if plan.get("replacement") in (None, "", False):
            warns.append("no replacement named; never pause a working ad without one ready")
        return blocks, warns, risks

    if action == "update":
        for ch in plan.get("changes", []):
            field, before, after = ch.get("field"), ch.get("before"), ch.get("after")
            if not ch.get("target"):
                blocks.append(f"change to {field} has no target id")
            if before is None:
                blocks.append(f"change to {field} has no `before` value; read the current value from the connector first")
            if field in ("objective", "optimization_goal"):
                blocks.append(f"{field} cannot be changed on a live ad set; that needs a new campaign")
            if field == "status" and str(after).upper() == "ACTIVE":
                blocks.append("turning something on is its own `activate` plan, not an update")
            if field in ("creative", "primary_text", "headline", "image", "video"):
                warns.append("editing a running ad's creative resets its learning; launch a new ad beside it instead")
            if field in ("daily_budget", "lifetime_budget"):
                b, a = num(before), num(after)
                if b and a and a > b:
                    step = (a - b) / b
                    risks.append(f"BUDGET UP {money(b)} -> {money(a)} a day (+{step:.0%})")
                    if step > MAX_STEP_UP:
                        warns.append(f"+{step:.0%} in one move; above +{MAX_STEP_UP:.0%} tends to throw the ad set back into learning")
                if a and ceiling_budget is not None and a > ceiling_budget:
                    blocks.append(f"new budget {money(a)} is over the owner's ceiling {money(ceiling_budget)}")
                if a and ceiling_budget is None:
                    blocks.append("owner has no max_daily_budget in their ads profile; no budget changes without one")
                if a:
                    risks.append(f"API value for {money(a)}: {int(round(a * 100))} (budgets are sent in cents)")
            if field == "targeting":
                risks.append("TARGETING CHANGE: resets learning")
        if not plan.get("changes"):
            blocks.append("update plan has no `changes`")
        return blocks, warns, risks

    # create
    camp, adset, ads = plan.get("campaign") or {}, plan.get("ad_set") or {}, plan.get("ads") or []
    risks.append("CREATES new objects, all PAUSED; nothing spends until a separate activate plan is approved")
    for label, obj in (("campaign", camp), ("ad set", adset)):
        st = str(obj.get("status", "PAUSED")).upper() if obj else "PAUSED"
        if st != "PAUSED":
            blocks.append(f"{label} status is {st}; everything is created PAUSED")
    for ad in ads:
        if str(ad.get("status", "PAUSED")).upper() != "PAUSED":
            blocks.append(f"ad '{ad.get('name')}' status is not PAUSED")

    if camp and not camp.get("existing_id"):
        objective = camp.get("objective")
        if objective != "OUTCOME_LEADS":
            warns.append(f"objective is {objective}; this desk plans lead campaigns (OUTCOME_LEADS). Say why if not")
        goal = adset.get("optimization_goal")
        if objective in OBJECTIVE_GOAL and goal and goal != OBJECTIVE_GOAL[objective]:
            blocks.append(f"optimization_goal {goal} does not match {objective} (needs {OBJECTIVE_GOAL[objective]})")
        cats = camp.get("special_ad_categories")
        if cats is None:
            cats = prof.get("special_ad_categories")
        if cats is None or cats == "unknown" or (isinstance(cats, list) and "unknown" in cats):
            blocks.append("special ad category unknown: ask whether the ads are about credit/loans/insurance/"
                          "financial services, jobs, housing, or social issues/politics")
        elif any(c not in SPECIAL_CATEGORIES for c in (cats if isinstance(cats, list) else [cats])):
            blocks.append(f"special_ad_categories has an unknown value: {cats}")
        elif cats not in ([], ["none"], "none"):
            warns.append("special ad category set: Meta limits age, gender, zip-code and lookalike targeting; "
                         "plan broad targeting")

    budget = num(camp.get("daily_budget")) if camp.get("daily_budget") is not None else num(adset.get("daily_budget"))
    if camp.get("daily_budget") is not None and adset.get("daily_budget") is not None:
        blocks.append("budget on both campaign and ad set; pick one (campaign = Meta spreads it, ad set = fixed)")
    if budget is None and not camp.get("existing_id"):
        blocks.append("no daily_budget on the campaign or ad set")
    if budget is not None:
        risks.append(f"NEW SPEND up to {money(budget)} a day once activated ({int(round(budget * 100))} in cents for the API)")
        if ceiling_budget is None:
            blocks.append("owner has no max_daily_budget in their ads profile; set one before planning spend")
        elif budget > ceiling_budget:
            blocks.append(f"daily budget {money(budget)} is over the owner's ceiling {money(ceiling_budget)}")

    if adset:
        dest = adset.get("destination") or prof.get("lead_method")
        page = adset.get("page_id") or prof.get("page_id")
        if not page:
            blocks.append("no page_id; lead ads need the Facebook Page they run from")
        if dest == "website":
            if not (adset.get("pixel_id") or prof.get("pixel_id")):
                blocks.append("website leads need a pixel (dataset) id; run meta-tracking first")
            if not all(a.get("url") for a in ads):
                blocks.append("website leads: every ad needs a destination url")
        elif dest == "instant_form":
            if not (adset.get("lead_form_id") or plan.get("lead_form")):
                blocks.append("instant form: name an existing lead_form_id or include a `lead_form` draft")
        else:
            blocks.append("ad set destination must be 'instant_form' or 'website'")
        tgt = adset.get("targeting") or {}
        countries = set(tgt.get("countries") or prof.get("countries") or [])
        if not countries and not tgt.get("regions") and not tgt.get("cities"):
            blocks.append("no location in targeting")
        if countries & EU_EEA and not (plan.get("dsa_beneficiary") and plan.get("dsa_payor")):
            blocks.append("ads reaching the EU need dsa_beneficiary and dsa_payor (who benefits, who pays)")
        if tgt.get("advantage_audience", True):
            amin, amax = tgt.get("age_min"), tgt.get("age_max")
            if (amin and amin > 25) or (amax and amax < 65):
                blocks.append("Advantage+ audience rejects narrow ages (needs min <= 25, max >= 65). "
                              "Widen the ages or turn Advantage+ audience off, and tell the owner the trade-off")
        if tgt.get("interests") and len(tgt.get("interests")) > 3:
            warns.append("many interests stacked; on Meta today the creative does the targeting. Go broad")
        for ex in ("interests", "behaviors", "demographics"):
            if (tgt.get("exclusions") or {}).get(ex):
                blocks.append(f"excluding {ex} is no longer allowed by Meta; only custom audiences can be excluded")

    tcpl = num(prof.get("target_cpl"))
    ceiling = ad_ceiling(budget, tcpl)
    if ceiling is not None and len(ads) > max(ceiling, 1):
        warns.append(f"{len(ads)} ads but the budget can feed about {ceiling} for a fair read; cut to the strongest")
    for ad in ads:
        for sev, msg in lint_copy(ad):
            (blocks if sev == "error" else warns).append(f"ad '{ad.get('name')}': {msg}")
        if not ad.get("asset") and not ad.get("existing_creative_id"):
            blocks.append(f"ad '{ad.get('name')}' has no image/video (asset) or existing creative")
    if not ads and not plan.get("existing_ads"):
        warns.append("no ads in the plan")
    return blocks, warns, risks


def render_plan(plan, pid, blocks, warns, risks):
    lines = [f"# Change plan {pid}: {plan.get('title') or plan.get('action')}", ""]
    lines.append(f"Account: {plan.get('account_id')} | Action: {plan.get('action')}")
    if plan.get("reason"):
        lines.append(f"Why: {plan['reason']}")
    lines.append("")
    lines.append("## What this does to money and delivery")
    lines += [f"- {r}" for r in risks] or ["- (none)"]
    if plan.get("action") == "update":
        lines.append("\n## Changes (before -> after)")
        for ch in plan.get("changes", []):
            lines.append(f"- {ch.get('target_name') or ch.get('target')}: {ch.get('field')} "
                         f"{ch.get('before')} -> {ch.get('after')}")
    if plan.get("action") == "create":
        c, s = plan.get("campaign") or {}, plan.get("ad_set") or {}
        lines.append("\n## What gets created (all PAUSED)")
        if c:
            lines.append(f"- Campaign: {c.get('name') or c.get('existing_id')} ({c.get('objective', 'existing')})")
        if s:
            lines.append(f"- Ad set: {s.get('name')} | {s.get('destination')} | {json.dumps(s.get('targeting') or {})}")
        for ad in plan.get("ads", []):
            lines.append(f"- Ad: {ad.get('name')} | headline: {ad.get('headline')}")
    if plan.get("action") in ("pause", "activate"):
        lines.append("\n## Targets")
        lines += [f"- {t}" for t in plan.get("targets", [])]
    lines.append("\n## How we'll know it worked")
    lines.append(plan.get("measure") or "- Read the objects back after the change and confirm every value matches this plan.")
    lines.append("\n## How to undo it")
    lines.append(plan.get("undo") or {"create": "- Nothing is live. Leave paused, or archive in Ads Manager.",
                                      "update": "- Set each field back to its `before` value.",
                                      "pause": "- Turn the same targets back on (a new activate plan).",
                                      "activate": "- Pause the same targets."}[plan.get("action")])
    if warns:
        lines.append("\n## Heads-up")
        lines += [f"- {w}" for w in warns]
    if blocks:
        lines.append("\n## BLOCKED: fix before asking for approval")
        lines += [f"- {b}" for b in blocks]
    else:
        lines.append(f"\nReady for the owner. Approval covers plan {pid} exactly; any change means a new plan id.")
    return "\n".join(lines) + "\n"


# ---------- commands ----------

PROFILE_TEMPLATE = {
    "business": "",
    "ad_account_id": "",
    "page_id": "",
    "instagram_account_id": "",
    "pixel_id": "",
    "currency": "USD",
    "countries": ["US"],
    "lead_method": "instant_form",
    "qualified_lead_means": "",
    "cost_per_customer_target": None,
    "lead_to_customer_rate": None,
    "target_cpl": None,
    "max_daily_budget": None,
    "special_ad_categories": "unknown",
    "notes": "Owner-confirmed. Written by meta-ads skills; the owner edits it by telling the agent.",
}
PROFILE_REQUIRED = ["ad_account_id", "page_id", "lead_method", "qualified_lead_means", "target_cpl",
                    "max_daily_budget", "special_ad_categories", "countries"]


def cmd_paths(args):
    cfg = load_config()
    b = brand_dir(cfg, args.business)
    o = out_dir(cfg, args.business)
    prof = b / PROFILE_NAME
    print(f"Drafts and reports: {o}")
    print(f"Ads profile:        {prof} ({'exists' if prof.exists() else 'missing: run profile init'})")
    print(f"Brand folder:       {b}")
    for f in BRAND_FILES:
        print(f"  {'ok     ' if (b / f).exists() else 'missing'} {f}")
    print(f"Launch log:         {o / 'launch-log.md'}")


def cmd_profile(args):
    cfg = load_config()
    if args.action == "init":
        d = brand_dir(cfg, args.business)
        path = d / PROFILE_NAME
        if path.exists():
            print(f"Already exists, not touched: {path}")
            return
        d.mkdir(parents=True, exist_ok=True)
        tpl = dict(PROFILE_TEMPLATE, business=args.business or "")
        path.write_text(json.dumps(tpl, indent=2) + "\n", encoding="utf-8")
        print(f"Created {path}. Fill it in with the owner, then run `meta.py profile check`.")
        return
    prof, path = load_profile(cfg, args.business)
    missing = []
    for k in PROFILE_REQUIRED:
        v = prof.get(k)
        if k == "special_ad_categories":
            if v in (None, "", "unknown") or (isinstance(v, list) and "unknown" in v):
                missing.append(k)      # [] or "none" is a real answer
        elif v in (None, "", [], "unknown"):
            missing.append(k)
    if prof.get("target_cpl") in (None, "") and prof.get("cost_per_customer_target") and prof.get("lead_to_customer_rate"):
        t = tcpl_from(num(prof["cost_per_customer_target"]), num(prof["lead_to_customer_rate"]))
        print(f"target_cpl can be set to {money(t)} (cost per customer x lead-to-customer rate). Confirm with the owner.")
    if prof.get("lead_method") not in ("instant_form", "website"):
        missing.append("lead_method (instant_form or website)")
    if prof.get("lead_method") == "website" and not prof.get("pixel_id"):
        missing.append("pixel_id (website leads)")
    print(f"Profile: {path}")
    if missing:
        print("Missing: " + ", ".join(dict.fromkeys(missing)))
        sys.exit(1)
    print("Complete.")


def cmd_tcpl(args):
    t = tcpl_from(args.cost_per_customer, args.lead_to_customer)
    if t is None:
        die("Need --cost-per-customer > 0 and --lead-to-customer between 0 and 1.")
    print(f"Target cost per qualified lead: {money(t)}")
    print(f"  = {money(args.cost_per_customer)} per customer x {args.lead_to_customer:.0%} of qualified leads becoming customers")
    print(f"Judge an ad after it spends {money(DATA_GATE_X * t)} (3x target).")
    if args.daily_budget:
        c = ad_ceiling(args.daily_budget, t)
        print(f"At {money(args.daily_budget)} a day the budget can feed about {c} ad(s) for a fair 14-day read.")
        wk = args.daily_budget * 7 / t
        print(f"At target cost that budget buys about {wk:.0f} qualified leads a week"
              + ("; under 50, so expect 'Learning limited'. Keep to one ad set." if wk < LEARNING_EVENTS else "."))


def cmd_audit(args):
    tcpl, daily = args.tcpl, args.daily_budget
    if (tcpl is None or daily is None) and (args.business or os.environ.get("BUZZ_AGENTS_CONFIG") or POINTER.exists()):
        try:
            cfg = load_config()
            prof, _ = load_profile(cfg, args.business, required=False)
        except SystemExit:
            prof = None
        if prof:
            tcpl = tcpl if tcpl is not None else num(prof.get("target_cpl"))
            daily = daily if daily is not None else num(prof.get("max_daily_budget"))
    rows, level, breakdown = normalise(read_rows(args.file))
    if not rows:
        die("No data rows found in that file.", 1)
    a = audit(rows, level, breakdown, tcpl=tcpl, daily_budget=daily, days=args.days)
    if args.json:
        print(json.dumps(a, indent=2, default=str))
    else:
        print_audit(a)


def cmd_plan(args):
    p = Path(args.file)
    if not p.exists():
        die(f"File not found: {p}")
    plan = json.loads(p.read_text(encoding="utf-8"))
    prof = None
    try:
        cfg = load_config()
        prof, _ = load_profile(cfg, args.business, required=False)
    except SystemExit:
        pass
    pid = plan_id(plan)
    blocks, warns, risks = check_plan(plan, prof)
    if args.json:
        print(json.dumps({"plan_id": pid, "blocked": blocks, "warnings": warns, "risks": risks}, indent=2))
    else:
        print(render_plan(plan, pid, blocks, warns, risks))
    sys.exit(1 if blocks else 0)


def cmd_copy(args):
    ads = load_ads(args.file)
    if not ads:
        die("No ads found. Use JSON (list of {name, primary_text, headline, description}) or markdown "
            "with '## Ad name' and 'Primary text:' / 'Headline:' / 'Description:' lines.", 1)
    report, errors = [], 0
    for ad in ads:
        issues = lint_copy(ad)
        errors += sum(1 for s, _ in issues if s == "error")
        report.append({"name": ad.get("name"), "issues": [{"severity": s, "message": m} for s, m in issues]})
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report:
            print(f"{r['name']}: " + ("clean" if not r["issues"] else ""))
            for i in r["issues"]:
                print(f"  {i['severity']:5} {i['message']}")
    sys.exit(1 if errors else 0)


def cmd_log(args):
    cfg = load_config()
    p = Path(args.file)
    plan = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    o = out_dir(cfg, args.business)
    o.mkdir(parents=True, exist_ok=True)
    log = o / "launch-log.md"
    if not log.exists():
        log.write_text("# Meta ads launch log\n\nOne line per approved change. Newest last.\n\n", encoding="utf-8")
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = (f"- {stamp} | plan {plan_id(plan) if plan else '?'} | {plan.get('action', '?')} | "
            f"{plan.get('title', p.name)} | result: {args.result}"
            + (f" | ids: {args.ids}" if args.ids else "") + (f" | {args.note}" if args.note else "") + "\n")
    with log.open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"Logged to {log}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Meta lead-gen ads helper (stdlib only).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("paths"); s.add_argument("--business"); s.set_defaults(fn=cmd_paths)
    s = sub.add_parser("profile"); s.add_argument("action", choices=["init", "check"])
    s.add_argument("--business"); s.set_defaults(fn=cmd_profile)
    s = sub.add_parser("tcpl"); s.add_argument("--cost-per-customer", type=float, required=True)
    s.add_argument("--lead-to-customer", type=float, required=True); s.add_argument("--daily-budget", type=float)
    s.set_defaults(fn=cmd_tcpl)
    s = sub.add_parser("audit"); s.add_argument("file"); s.add_argument("--tcpl", type=float)
    s.add_argument("--daily-budget", type=float); s.add_argument("--days", type=int)
    s.add_argument("--business"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_audit)
    s = sub.add_parser("plan"); s.add_argument("file"); s.add_argument("--business")
    s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("copy"); s.add_argument("file"); s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_copy)
    s = sub.add_parser("log"); s.add_argument("file"); s.add_argument("--result", required=True,
                                                                        choices=["verified", "failed", "unknown"])
    s.add_argument("--ids"); s.add_argument("--note"); s.add_argument("--business"); s.set_defaults(fn=cmd_log)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
