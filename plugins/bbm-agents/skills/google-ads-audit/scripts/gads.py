#!/usr/bin/env python3
"""Google Ads facts for the owner's own account. Stdlib only; macOS, Linux, Windows.

Reads the account through the owner's Composio connection (`composio proxy`, Google Ads API).
Read-only: nothing here creates, changes, pauses or deletes anything in Google Ads.
Deterministic facts only. Judgement (what matters, what to do first) is the agent's job.

  gads.py paths [--business NAME]              # where reports go, brand files, the chosen account
  gads.py accounts                             # accounts this login can reach: name, status, 30-day spend
  gads.py use CUSTOMER_ID [--login MANAGER_ID] # remember which account to work on (writes account.json)
  gads.py geo "City, ST" [--country US]        # find location IDs for keyword research and targeting
  gads.py keywords ideas --seed "a" [--seed "b"] [--url URL] --geo ID [--lang 1000] [--limit 80]
  gads.py keywords volume "kw one" "kw two" | --file list.txt  --geo ID [--lang 1000]
                                               # Google Keyword Planner: monthly searches, competition,
                                               #   top-of-page bid range. Saves CSV + JSON.
  gads.py budget --daily 50 --cpc 6.5 [--cvr 0.06] [--lead-value 900] [--close-rate 0.25]
                                               # what a budget buys; whether smart bidding can learn
  gads.py blueprint check FILE.json            # validate a campaign blueprint (limits, structure, conflicts)
  gads.py blueprint render FILE.json [--out F] # the blueprint as a build sheet (markdown)
  gads.py fetch [--days 30]                    # pull the account's audit data into a dated folder
  gads.py audit DATA_DIR [--goal leads|sales|calls|awareness] [--target-cpa N] [--target-roas N]
                [--brand TERM ...] [--answers F] [--blueprint F] [--check-urls] [--json] [--out F]
                                               # score the account on 14 categories; list what to ask

Common flags: --business NAME (workspaces with one brand per business), --insecure (URL checks only).
Env: GOOGLE_ADS_API_VERSION (pin e.g. v23), COMPOSIO_BIN (path to composio), GOOGLE_ADS_COMPOSIO_ACCOUNT
     (which Composio connection to use when there are several).
Exit codes: 0 ok, 1 API or check failed, 2 config or usage problem.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import ssl
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
API_HOST = "https://googleads.googleapis.com"
API_VERSIONS = ["v25", "v24", "v23"]   # newest first; the first one that answers is used
UA = "Mozilla/5.0 (compatible; bbm-gads-check/1.0; +https://github.com/Brand-Building-Machine/bbm-buzz-agents)"

# Google Ads limits (Google Ads Help, responsive search ads and assets).
HEADLINE_MAX, DESCRIPTION_MAX, PATH_MAX = 30, 90, 15
HEADLINES_MIN, HEADLINES_MAX, HEADLINES_GOOD = 3, 15, 10
DESCRIPTIONS_MIN, DESCRIPTIONS_MAX, DESCRIPTIONS_GOOD = 2, 4, 4
SITELINK_TEXT_MAX, SITELINK_DESC_MAX, CALLOUT_MAX, SNIPPET_VALUE_MAX = 25, 35, 25, 25
KEYWORDS_PER_GROUP = (3, 20)        # themed ad groups: a handful to ~20 keywords sharing one promise
SMART_BIDDING_MIN = 15              # conversions/month before Maximize Conversions has much to learn from
TARGET_BIDDING_MIN = 30             # conversions/month before a CPA/ROAS target is reliable
DAYS_PER_MONTH = 30.4

# Optmyzr category weights (Apache-2.0, see CREDITS.md). Keys are category numbers.
CATEGORIES = {
    1: ("Account & settings", 5), 2: ("Conversion tracking", 12), 3: ("Campaign structure", 7),
    4: ("Performance Max & other channels", 8), 5: ("Budgets & spend", 7), 6: ("Bidding", 8),
    7: ("Targeting", 5), 8: ("Audiences", 6), 9: ("Keywords", 7), 10: ("Quality Score", 10),
    11: ("Search terms & negatives", 10), 12: ("Ads", 8), 13: ("Assets", 4), 14: ("Landing pages", 3),
}
POINTS = {"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0}
LEAD_CATEGORIES = {"SUBMIT_LEAD_FORM", "CONTACT", "PHONE_CALL_LEAD", "IMPORTED_LEAD", "QUALIFIED_LEAD",
                   "CONVERTED_LEAD", "REQUEST_QUOTE", "BOOK_APPOINTMENT", "SIGNUP", "GET_DIRECTIONS"}
MICRO_CATEGORIES = {"PAGE_VIEW", "ENGAGEMENT", "ADD_TO_CART", "BEGIN_CHECKOUT"}
NON_SMART = {"MANUAL_CPC", "ENHANCED_CPC", "TARGET_SPEND", "MAXIMIZE_CLICKS", "MANUAL_CPM", "MANUAL_CPV"}
TARGET_BIDS = {"TARGET_CPA", "TARGET_ROAS"}
DASHES = re.compile("[—–]")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class ApiError(Exception):
    pass


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
    return json.loads(path.read_text(encoding="utf-8"))


def brand_dir(cfg, business):
    pattern = cfg.get("BRAND_PATH") or ""
    if not pattern:
        return None
    if "{business}" in pattern:
        if not business:
            return None
        return Path(pattern.replace("{business}", business)).expanduser()
    return Path(pattern).expanduser()


def out_dir(business=None, create=True):
    cfg = load_config()
    if not cfg.get("PROPOSED_PATH"):
        die("Config has no PROPOSED_PATH. Run workspace-config.")
    out = Path(cfg["PROPOSED_PATH"]).expanduser() / "google-ads"
    if business:
        out = out / slug(business)
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "x"


def read_json(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16"):   # PowerShell `>` writes UTF-16
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, ValueError):
            continue
    die(f"Can't read {path} as JSON.")


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_account(business, customer=None, login=None):
    if customer:
        return {"customer_id": clean_id(customer), "login_customer_id": clean_id(login) if login else None}
    f = out_dir(business, create=False) / "account.json"
    if not f.exists():
        die("No Google Ads account chosen yet. Run `gads.py accounts`, then `gads.py use <customer id>`.")
    return read_json(f)


def clean_id(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 10:
        die(f"'{value}' isn't a Google Ads customer ID (10 digits, like 123-456-7890).")
    return digits


# ---------- API through composio ----------

_version = [os.environ.get("GOOGLE_ADS_API_VERSION")]


WSL_SHIM = 'export PATH="$HOME/.local/bin:$HOME/.composio:$PATH"; exec composio "$@"'


def composio_cmd():
    """The command prefix that runs composio. On Windows the CLI lives inside WSL."""
    exe = os.environ.get("COMPOSIO_BIN") or shutil.which("composio")
    if exe:
        return [exe]
    if os.name == "nt" and shutil.which("wsl"):
        return ["wsl", "-e", "sh", "-c", WSL_SHIM, "sh"]
    die("The composio CLI isn't installed or isn't on PATH. Setup: references/connect-composio.md in the "
        "google-ads-audit skill (install, `composio login`, `composio link googleads`).")


def composio_bin():
    return composio_cmd()[0]


TRANSIENT = ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED", "429", "503", "took over")


def api(method, path, body=None, login=None, tries=3):
    """One Google Ads API call through `composio proxy`, retrying rate limits and hiccups."""
    for attempt in range(tries):
        try:
            return _api_once(method, path, body, login)
        except ApiError as e:
            if attempt == tries - 1 or not any(t in str(e) for t in TRANSIENT):
                raise
            time.sleep(2 * (attempt + 1))


def _api_once(method, path, body=None, login=None):
    cmd = composio_cmd()
    versions = [_version[0]] if _version[0] else API_VERSIONS
    last = ""
    for ver in versions:
        args = cmd + ["proxy", f"{API_HOST}/{ver}/{path}", "--toolkit", "googleads", "-X", method]
        if body is not None:   # body over stdin: no shell or WSL quoting of JSON
            args += ["-H", "content-type: application/json", "-d", "-"]
        if login:
            args += ["-H", f"login-customer-id: {login}"]
        if os.environ.get("GOOGLE_ADS_COMPOSIO_ACCOUNT"):
            args += ["--account", os.environ["GOOGLE_ADS_COMPOSIO_ACCOUNT"]]
        try:
            # Always give stdin: composio reads it when it isn't a terminal and would otherwise wait forever.
            p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               input=json.dumps(body) if body is not None else "", timeout=120)
        except subprocess.TimeoutExpired:
            raise ApiError("composio took over 2 minutes to answer; try again, or check `composio whoami`.")
        out = (p.stdout or "").strip()
        if out.lower().startswith("<!doctype html") or out.lower().startswith("<html"):
            last = f"API version {ver} not available"
            if _version[0]:
                raise ApiError(f"Google Ads API {ver} answered 404. Unset GOOGLE_ADS_API_VERSION or pin a newer one.")
            continue
        try:
            data = json.loads(out)
        except ValueError:
            msg = (out or p.stderr or "").strip()[:400]
            if "link" in msg.lower() or "connect" in msg.lower():
                msg += "\nIs Google Ads linked? Run `composio link googleads`."
            raise ApiError(f"composio returned something that isn't JSON: {msg}")
        _version[0] = ver
        if isinstance(data, dict) and "error" in data:
            raise ApiError(explain_error(data["error"]))
        if isinstance(data, list) and data and isinstance(data[0], dict) and "error" in data[0]:
            raise ApiError(explain_error(data[0]["error"]))
        return data
    raise ApiError(f"No Google Ads API version answered ({last}). Set GOOGLE_ADS_API_VERSION to a current one.")


HINTS = {
    "CUSTOMER_NOT_ENABLED": "That account is cancelled, suspended or not finished setting up.",
    "USER_PERMISSION_DENIED": "This login reaches that account only through a manager (MCC). "
                              "Pass --login <manager customer id>.",
    "CUSTOMER_NOT_FOUND": "No account with that ID is reachable from this login.",
    "DEVELOPER_TOKEN_NOT_APPROVED": "The API developer token behind the connection isn't approved for live accounts.",
    "NOT_ADS_USER": "The Google login linked in Composio has no Google Ads access.",
}


def explain_error(err):
    if isinstance(err, str):
        return err
    parts = []
    for det in err.get("details", []) or []:
        for e in det.get("errors", []) or []:
            code = next(iter((e.get("errorCode") or {}).values()), "")
            hint = HINTS.get(code, "")
            parts.append(f"{code}: {e.get('message', '')} {hint}".strip())
    return "; ".join(parts) or f"{err.get('status', '')} {err.get('message', '')}".strip()


def search(customer, query, login=None):
    rows, token = [], None
    while True:
        body = {"query": query}
        if token:
            body["pageToken"] = token
        data = api("POST", f"customers/{customer}/googleAds:search", body, login)
        rows += data.get("results", []) or []
        token = data.get("nextPageToken")
        if not token:
            return rows


def g(row, *path, default=None):
    """Nested get: g(row, 'campaign', 'id')."""
    cur = row
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def micros(value):
    return num(value) / 1_000_000


# ---------- paths / accounts / use ----------

def cmd_paths(a):
    cfg = load_config()
    out = out_dir(a.business)
    print(f"reports:  {out}")
    acct = out / "account.json"
    if acct.exists():
        info = read_json(acct)
        print(f"account:  {fmt_id(info.get('customer_id', ''))} {info.get('name', '')}")
    else:
        print("account:  not chosen yet (gads.py accounts, then gads.py use <id>)")
    bd = brand_dir(cfg, a.business)
    if bd is None:
        print("brand:    BRAND_PATH has {business}; pass --business <name>" if "{business}" in (cfg.get("BRAND_PATH") or "")
              else "brand:    no BRAND_PATH in config")
    else:
        print(f"brand:    {bd}")
        for f in ("brand-bible.md", "voice-agent.md", "offers.md"):
            print(f"  {'ok     ' if (bd / f).exists() else 'missing'} {f}")
    bp = sorted(out.glob("*blueprint*.json"))
    print(f"blueprints: {', '.join(p.name for p in bp) if bp else 'none yet'}")
    found = os.environ.get("COMPOSIO_BIN") or shutil.which("composio")
    if not found and os.name == "nt" and shutil.which("wsl"):
        found = "inside WSL (wsl composio)"
    print(f"composio: {found or 'NOT FOUND (see references/connect-composio.md)'}")


def account_info(cid, login=None):
    rows = search(cid, "SELECT customer.id, customer.descriptive_name, customer.manager, customer.status, "
                       "customer.currency_code, customer.time_zone FROM customer", login)
    return rows[0]["customer"] if rows else {}


def cmd_accounts(a):
    try:
        data = api("GET", "customers:listAccessibleCustomers")
    except ApiError as e:
        die(f"Couldn't list accounts: {e}", 1)
    ids = [r.split("/")[-1] for r in data.get("resourceNames", [])]
    hidden = [i for i in ids if not i.isdigit()]
    ids = [i for i in ids if i.isdigit()]
    if a.manager:
        ids.insert(0, clean_id(a.manager))
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=29)
    seen, lines = set(), []

    def spend(cid, login):
        try:
            r = search(cid, f"SELECT metrics.cost_micros, metrics.conversions FROM customer "
                            f"WHERE segments.date BETWEEN '{start}' AND '{end}'", login)
            return micros(g(r[0], "metrics", "costMicros")) if r else 0.0, num(g(r[0], "metrics", "conversions")) if r else 0.0
        except ApiError:
            return None, None

    def probe(cid):
        try:
            return cid, account_info(cid, cid), None
        except ApiError as e:
            return cid, None, str(e)

    with ThreadPoolExecutor(max_workers=8) as pool:
        infos = list(pool.map(probe, ids))
    todo = []   # (cid, name, status, access, login, currency) needing a spend lookup
    for cid, info, err in infos:
        if err:
            lines.append((cid, err.split(":")[0][:40], "UNREACHABLE", "", None, None, ""))
            continue
        if info.get("manager"):
            lines.append((cid, info.get("descriptiveName", ""), info.get("status", ""), "MANAGER", None, None, ""))
            try:
                kids = search(cid, "SELECT customer_client.id, customer_client.descriptive_name, customer_client.status, "
                                   "customer_client.manager, customer_client.currency_code FROM customer_client "
                                   "WHERE customer_client.level = 1", cid)
            except ApiError:
                kids = []
            for k in kids:
                c = k["customerClient"]
                if not c.get("manager") and c.get("status") == "ENABLED":
                    todo.append((c["id"], c.get("descriptiveName", ""), "ENABLED", f"via {fmt_id(cid)}", cid,
                                 c.get("currencyCode", "")))
        elif info.get("status") == "ENABLED":
            todo.append((cid, info.get("descriptiveName", ""), "ENABLED", "direct", cid, info.get("currencyCode", "")))
        else:
            lines.append((cid, info.get("descriptiveName", ""), info.get("status", ""), "direct", None, None, ""))
    uniq = []
    for t in sorted(todo, key=lambda t: t[3] != "direct"):   # prefer direct access over via-manager
        if t[0] not in seen:
            seen.add(t[0])
            uniq.append(t)
    with ThreadPoolExecutor(max_workers=8) as pool:
        spends = list(pool.map(lambda t: spend(t[0], t[4]), uniq))
    for (cid, name, status, access, _, cur), (s, conv) in zip(uniq, spends):
        lines.append((cid, name, status, access, s, conv, cur))
    if hidden and not a.manager:
        lines.append(("(hidden)", "Composio masks this ID (usually the manager account saved on the connection). "
                      "If it's your manager (MCC), re-run with --manager <its id> to list the accounts under it.",
                      "", "", None, None, ""))
    print(f"{'customer id':13} {'status':10} {'access':16} {'30-day spend':>14} {'conv':>7}  name")
    for cid, name, status, access, s, conv, extra in lines:
        sp = f"{s:,.2f} {extra}" if s is not None else ""
        cv = f"{conv:,.1f}" if conv is not None else ""
        print(f"{fmt_id(cid):13} {status:10} {access:16} {sp:>14} {cv:>7}  {name}")
    print("\nPick one with `gads.py use <customer id>` (add --login <manager id> for 'via' accounts).")


def fmt_id(cid):
    cid = str(cid)
    return f"{cid[:3]}-{cid[3:6]}-{cid[6:]}" if len(cid) == 10 else cid


def cmd_use(a):
    cid = clean_id(a.customer_id)
    login = clean_id(a.login) if a.login else None
    try:
        info = account_info(cid, login or cid)
    except ApiError as e:
        die(f"Can't read account {fmt_id(cid)}: {e}", 1)
    if info.get("manager"):
        die(f"{fmt_id(cid)} is a manager (MCC) account. Pick one of the accounts under it; `gads.py accounts` lists them.", 2)
    data = {"customer_id": cid, "login_customer_id": login or cid, "name": info.get("descriptiveName", ""),
            "status": info.get("status", ""), "currency": info.get("currencyCode", ""),
            "time_zone": info.get("timeZone", ""), "chosen": str(dt.date.today())}
    f = out_dir(a.business) / "account.json"
    write_json(f, data)
    print(f"Using {fmt_id(cid)} {data['name']} ({data['status']}, {data['currency']}, {data['time_zone']}). Saved {f}")
    if data["status"] != "ENABLED":
        print("Note: this account isn't enabled, so it has no live data. Keyword research still works.")


# ---------- geo + keyword planner ----------

def cmd_geo(a):
    body = {"locale": "en", "locationNames": {"names": [a.name]}}
    if a.country:
        body["countryCode"] = a.country.upper()
    try:
        data = api("POST", "geoTargetConstants:suggest", body)
    except ApiError as e:
        die(f"Location lookup failed: {e}", 1)
    sugg = data.get("geoTargetConstantSuggestions", [])
    if not sugg:
        die(f"No locations match '{a.name}'. Try just the city, or the state.", 1)
    print(f"{'id':>10}  {'type':16} name")
    for s in sugg[:12]:
        c = s["geoTargetConstant"]
        print(f"{c['id']:>10}  {c.get('targetType', ''):16} {c.get('canonicalName', c.get('name'))}")
    print("\nCommon: 2840 United States, 2124 Canada, 2826 United Kingdom, 2036 Australia.")


def planner_rows(results, key):
    out = []
    for r in results:
        m = r.get(key) or {}
        monthly = [(x.get("year"), x.get("month"), int(num(x.get("monthlySearches")))) for x in m.get("monthlySearchVolumes", [])]
        out.append({
            "keyword": r.get("text", ""),
            "avg_monthly_searches": int(num(m.get("avgMonthlySearches"))),
            "competition": m.get("competition", "UNSPECIFIED"),
            "competition_index": int(num(m.get("competitionIndex"))),
            "low_top_of_page_bid": round(micros(m.get("lowTopOfPageBidMicros")), 2),
            "high_top_of_page_bid": round(micros(m.get("highTopOfPageBidMicros")), 2),
            "trend_12m": [v for _, _, v in monthly][-12:],
            "close_variants": r.get("closeVariants", []),
        })
    return out


def cmd_keywords(a):
    acct = load_account(a.business, a.customer, a.login)
    cid, login = acct["customer_id"], acct.get("login_customer_id")
    geos = [f"geoTargetConstants/{re.sub(r'[^0-9]', '', x)}" for x in a.geo]
    base = {"language": f"languageConstants/{a.lang}", "geoTargetConstants": geos,
            "keywordPlanNetwork": "GOOGLE_SEARCH"}
    try:
        if a.mode == "ideas":
            if not a.seed and not a.url:
                die("Give at least one --seed keyword or a --url.", 2)
            body = dict(base, includeAdultKeywords=False, pageSize=min(a.limit, 1000))
            if a.seed and a.url:
                body["keywordAndUrlSeed"] = {"url": a.url, "keywords": a.seed}
            elif a.url:
                body["urlSeed"] = {"url": a.url}
            else:
                body["keywordSeed"] = {"keywords": a.seed}
            data = api("POST", f"customers/{cid}:generateKeywordIdeas", body, login)
            rows = planner_rows(data.get("results", []), "keywordIdeaMetrics")[:a.limit]
            label = "-".join(a.seed[:2]) if a.seed else urllib.parse.urlparse(a.url).netloc
        else:
            kws = list(a.keyword)
            if a.file:
                kws += [ln.strip() for ln in Path(a.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            kws = list(dict.fromkeys(k.lower() for k in kws))
            if not kws:
                die("Give keywords to check, or --file with one per line.", 2)
            rows = []
            for i in range(0, len(kws), 1000):
                data = api("POST", f"customers/{cid}:generateKeywordHistoricalMetrics",
                           dict(base, keywords=kws[i:i + 1000]), login)
                rows += planner_rows(data.get("results", []), "keywordMetrics")
            found = {r["keyword"] for r in rows} | {v for r in rows for v in r["close_variants"]}
            for k in kws:
                if k not in found:
                    rows.append({"keyword": k, "avg_monthly_searches": 0, "competition": "NO DATA",
                                 "competition_index": 0, "low_top_of_page_bid": 0, "high_top_of_page_bid": 0,
                                 "trend_12m": [], "close_variants": []})
            label = "volume-" + kws[0]
    except ApiError as e:
        die(f"Keyword Planner failed: {e}", 1)
    rows.sort(key=lambda r: -r["avg_monthly_searches"])
    cur = acct.get("currency", "")
    print(f"{'searches/mo':>11}  {'comp':6} {'top-of-page bid ' + cur:>22}  keyword")
    for r in rows:
        bid = f"{r['low_top_of_page_bid']:.2f}-{r['high_top_of_page_bid']:.2f}" if r["high_top_of_page_bid"] else "n/a"
        print(f"{r['avg_monthly_searches']:>11,}  {r['competition'][:6]:6} {bid:>22}  {r['keyword']}")
    folder = out_dir(a.business) / "keywords"
    folder.mkdir(exist_ok=True)
    stem = folder / f"{dt.date.today()}-{slug(label)}"
    write_json(stem.with_suffix(".json"), {"geo": a.geo, "lang": a.lang, "mode": a.mode, "seed": a.seed, "url": a.url,
                                           "currency": cur, "rows": rows})
    with open(stem.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid"])
        for r in rows:
            w.writerow([r["keyword"], r["avg_monthly_searches"], r["competition"], r["low_top_of_page_bid"],
                        r["high_top_of_page_bid"]])
    print(f"\n{len(rows)} keywords. Saved {stem.with_suffix('.csv')} and .json")
    print("Volumes are Google's rounded estimates for the chosen locations; bids are the range advertisers "
          "paid to show at the top of the page. Low-volume terms can still be the best leads.")


# ---------- budget math ----------

def budget_math(daily=None, monthly=None, cpc=None, cvr=None, lead_value=None, close_rate=None):
    if not cpc or cpc <= 0:
        raise ValueError("cpc must be > 0")
    monthly = monthly if monthly else (daily or 0) * DAYS_PER_MONTH
    daily = monthly / DAYS_PER_MONTH
    r = {"daily": round(daily, 2), "monthly": round(monthly, 2), "cpc": cpc,
         "clicks_per_month": round(monthly / cpc, 1)}
    if cvr:
        conv = monthly / cpc * cvr
        r["conversions_per_month"] = round(conv, 1)
        r["cpa"] = round(cpc / cvr, 2)
        r["smart_bidding"] = ("enough for a CPA/ROAS target" if conv >= TARGET_BIDDING_MIN else
                              "enough for Maximize Conversions, not yet a target" if conv >= SMART_BIDDING_MIN else
                              "thin: Maximize Clicks or Manual CPC with a cap, or raise budget or narrow scope")
        r["budget_for_15_conversions"] = round(SMART_BIDDING_MIN * cpc / cvr, 2)
        r["budget_for_30_conversions"] = round(TARGET_BIDDING_MIN * cpc / cvr, 2)
        if lead_value:
            r["break_even_cpa"] = round(lead_value * (close_rate or 1), 2)
            r["profitable_at_estimate"] = r["cpa"] <= r["break_even_cpa"]
    return r


def cmd_budget(a):
    try:
        r = budget_math(a.daily, a.monthly, a.cpc, a.cvr, a.lead_value, a.close_rate)
    except ValueError as e:
        die(str(e))
    if a.json:
        print(json.dumps(r, indent=2))
        return
    print(f"Budget {r['daily']:,.2f}/day = {r['monthly']:,.2f}/month at {r['cpc']:,.2f} per click "
          f"= about {r['clicks_per_month']:,.0f} clicks/month.")
    if "conversions_per_month" in r:
        print(f"At a {a.cvr:.1%} conversion rate: about {r['conversions_per_month']:,.1f} conversions/month, "
              f"cost per conversion about {r['cpa']:,.2f}.")
        print(f"Smart bidding: {r['smart_bidding']}.")
        print(f"Budget needed for 15 conversions/month: {r['budget_for_15_conversions']:,.2f}; "
              f"for 30: {r['budget_for_30_conversions']:,.2f}.")
    if "break_even_cpa" in r:
        print(f"Break-even cost per lead: {r['break_even_cpa']:,.2f} "
              f"({'estimate is under it' if r['profitable_at_estimate'] else 'estimate is OVER it'}).")
    print("These are planning estimates from the inputs, not a forecast. The first 30 days of real data replace them.")


# ---------- blueprint ----------

def kw_match_blocks(neg_text, neg_match, kw_text):
    """Would this negative block this keyword's core query? Google negative matching (no close variants)."""
    n, k = neg_text.lower().split(), kw_text.lower().split()
    if not n:
        return False
    if neg_match == "EXACT":
        return n == k
    if neg_match == "PHRASE":
        return any(k[i:i + len(n)] == n for i in range(len(k) - len(n) + 1))
    return set(n) <= set(k)   # BROAD: all words, any order


def parse_kw(item):
    """Accept {'text','match'} or a string in Google's notation: [exact], "phrase", broad."""
    if isinstance(item, dict):
        return item.get("text", "").strip(), (item.get("match") or "PHRASE").upper()
    s = str(item).strip()
    if s.startswith("[") and s.endswith("]"):
        return s[1:-1].strip(), "EXACT"
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1].strip(), "PHRASE"
    return s, "BROAD"


def check_blueprint(bp):
    """Return a list of (level, where, message). level: error | warn."""
    out = []

    def add(level, where, msg):
        out.append((level, where, msg))

    def text_rules(where, s, limit, kind):
        if len(s) > limit:
            add("error", where, f"{kind} is {len(s)} characters; the limit is {limit}: {s!r}")
        if DASHES.search(s):
            add("error", where, f"{kind} contains an em/en dash; use a comma or colon: {s!r}")
        if kind == "headline" and "!" in s:
            add("error", where, f"Google doesn't allow '!' in headlines: {s!r}")
        letters = [c for c in s if c.isalpha()]
        if len(letters) > 4 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
            add("error", where, f"{kind} is mostly capitals; Google disapproves excessive caps: {s!r}")
        if "  " in s or s != s.strip():
            add("warn", where, f"{kind} has extra spaces: {s!r}")

    for key in ("business", "goal", "campaigns"):
        if not bp.get(key):
            add("error", "blueprint", f"missing '{key}'")
    if bp.get("goal") and bp["goal"] not in ("leads", "sales", "calls", "store_visits", "awareness"):
        add("warn", "blueprint", f"goal '{bp['goal']}' isn't one of leads, sales, calls, store_visits, awareness")
    conv = bp.get("conversions") or {}
    prim = conv.get("primary") or []
    if not prim:
        add("error", "conversions", "no primary conversion defined; smart bidding needs one real business outcome")
    if len(prim) > 3:
        add("warn", "conversions", f"{len(prim)} primary conversions; keep 1-3 real outcomes, the rest secondary")
    for c in prim:
        if (c.get("category") or "").upper() in MICRO_CATEGORIES:
            add("error", "conversions", f"'{c.get('name')}' is a micro-event ({c.get('category')}); make it secondary")
    econ = bp.get("economics") or {}
    geo = bp.get("geo") or {}
    if not geo.get("locations"):
        add("error", "geo", "no locations; a campaign without locations shows worldwide")
    if (geo.get("type") or "PRESENCE").upper() != "PRESENCE":
        add("warn", "geo", "location option should be PRESENCE (people in the area), not presence-or-interest")

    total_daily, seen_kw = 0.0, {}
    brand_terms = [t.lower() for t in bp.get("brand_terms") or []]
    account_negs = [parse_kw(n) for n in (bp.get("negatives") or {}).get("account", [])]
    for ci, camp in enumerate(bp.get("campaigns") or []):
        cname = camp.get("name") or f"campaign {ci + 1}"
        ctype = (camp.get("type") or "SEARCH").upper()
        daily = num(camp.get("budget_daily"))
        total_daily += daily
        if daily <= 0:
            add("error", cname, "no daily budget")
        bidding = (camp.get("bidding") or "").upper()
        if not bidding:
            add("error", cname, "no bidding strategy")
        if bidding == "ENHANCED_CPC":
            add("error", cname, "Enhanced CPC is retired; use Maximize Conversions or Manual CPC")
        exp = num(camp.get("expected_conversions_month"), None)
        if bidding in TARGET_BIDS and exp is not None and exp < TARGET_BIDDING_MIN:
            add("warn", cname, f"{bidding} with ~{exp:.0f} conversions/month expected; start on Maximize Conversions "
                               f"and add a target after {TARGET_BIDDING_MIN}+/month")
        nets = camp.get("networks") or {}
        if ctype == "SEARCH" and nets.get("display", False):
            add("warn", cname, "Display Network is on for a Search campaign; keep it off until Search is proven")
        if ctype == "SEARCH" and nets.get("search_partners", False):
            add("warn", cname, "Search Partners is on; most new accounts start with it off")
        camp_negs = [parse_kw(n) for n in camp.get("negatives", [])]
        groups = camp.get("ad_groups") or []
        if ctype == "SEARCH" and not groups:
            add("error", cname, "Search campaign with no ad groups")
        is_brand_camp = "brand" in cname.lower() and "non" not in cname.lower()
        if brand_terms and ctype == "SEARCH" and not is_brand_camp:
            if not any(any(bt in t.lower() for bt in brand_terms) for t, _ in camp_negs + account_negs):
                add("warn", cname, "non-brand campaign without your brand name as a negative; brand searches "
                                   "should go to the brand campaign")
        for gi, grp in enumerate(groups):
            gname = f"{cname} > {grp.get('name') or f'ad group {gi + 1}'}"
            if not grp.get("landing_page"):
                add("error", gname, "no landing page")
            elif urllib.parse.urlparse(grp["landing_page"]).path in ("", "/") and not is_brand_camp:
                add("warn", gname, "landing page is the homepage; a page that matches this ad group converts better")
            kws = [parse_kw(k) for k in grp.get("keywords", [])]
            if ctype == "SEARCH":
                if not kws:
                    add("error", gname, "no keywords")
                elif not KEYWORDS_PER_GROUP[0] <= len(kws) <= KEYWORDS_PER_GROUP[1]:
                    add("warn", gname, f"{len(kws)} keywords; themed groups usually hold "
                                       f"{KEYWORDS_PER_GROUP[0]}-{KEYWORDS_PER_GROUP[1]} sharing one promise")
            for text, match in kws:
                if match not in ("EXACT", "PHRASE", "BROAD"):
                    add("error", gname, f"keyword '{text}' has match type '{match}'")
                key = (text.lower(), match)
                if key in seen_kw and seen_kw[key] != gname:
                    add("error", gname, f"'{text}' ({match}) is also in {seen_kw[key]}; one home per keyword")
                seen_kw.setdefault(key, gname)
                if match == "BROAD" and bidding in NON_SMART:
                    add("warn", gname, f"broad match '{text}' with {bidding}; broad needs smart bidding and "
                                       f"a solid negative list")
                for ntext, nmatch in camp_negs + account_negs + [parse_kw(n) for n in grp.get("negatives", [])]:
                    if kw_match_blocks(ntext, nmatch, text):
                        add("error", gname, f"negative '{ntext}' ({nmatch}) blocks your own keyword '{text}'")
            ads = grp.get("ads") or []
            if ctype == "SEARCH" and not ads:
                add("error", gname, "no responsive search ad")
            for ai, ad in enumerate(ads):
                where = f"{gname} > ad {ai + 1}"
                hs, ds = ad.get("headlines") or [], ad.get("descriptions") or []
                if len(hs) < HEADLINES_MIN or len(hs) > HEADLINES_MAX:
                    add("error", where, f"{len(hs)} headlines; Google needs {HEADLINES_MIN}-{HEADLINES_MAX}")
                elif len(hs) < HEADLINES_GOOD:
                    add("warn", where, f"{len(hs)} headlines; {HEADLINES_GOOD}-{HEADLINES_MAX} gives Google room to test")
                if len(ds) < DESCRIPTIONS_MIN or len(ds) > DESCRIPTIONS_MAX:
                    add("error", where, f"{len(ds)} descriptions; Google needs {DESCRIPTIONS_MIN}-{DESCRIPTIONS_MAX}")
                elif len(ds) < DESCRIPTIONS_GOOD:
                    add("warn", where, f"{len(ds)} descriptions; use all {DESCRIPTIONS_GOOD}")
                lowered = [h.lower() for h in hs]
                for dup in {h for h in lowered if lowered.count(h) > 1}:
                    add("error", where, f"duplicate headline: {dup!r}")
                for h in hs:
                    text_rules(where, h, HEADLINE_MAX, "headline")
                for d in ds:
                    text_rules(where, d, DESCRIPTION_MAX, "description")
                for p in (ad.get("path1"), ad.get("path2")):
                    if p and len(p) > PATH_MAX:
                        add("error", where, f"display path '{p}' over {PATH_MAX} characters")
                if kws and not any(any(w in h.lower() for w in kws[0][0].lower().split() if len(w) > 3) for h in hs):
                    add("warn", where, "no headline echoes the ad group's main keyword; ad relevance suffers")
    assets = bp.get("assets") or {}
    sl = assets.get("sitelinks") or []
    if len(sl) < 4:
        add("warn", "assets", f"{len(sl)} sitelinks; use at least 4")
    for s in sl:
        text_rules("assets > sitelink", s.get("text", ""), SITELINK_TEXT_MAX, "sitelink text")
        for d in (s.get("desc1"), s.get("desc2")):
            if d:
                text_rules("assets > sitelink", d, SITELINK_DESC_MAX, "sitelink description")
        if not s.get("url"):
            add("error", "assets > sitelink", f"sitelink '{s.get('text')}' has no URL")
    co = assets.get("callouts") or []
    if len(co) < 4:
        add("warn", "assets", f"{len(co)} callouts; use at least 4")
    for c in co:
        text_rules("assets > callout", c, CALLOUT_MAX, "callout")
    for sn in assets.get("snippets") or []:
        vals = sn.get("values") or []
        if len(vals) < 3:
            add("error", "assets > snippet", f"snippet '{sn.get('header')}' needs at least 3 values")
        for v in vals:
            text_rules("assets > snippet", v, SNIPPET_VALUE_MAX, "snippet value")
    if bp.get("goal") in ("leads", "calls") and not assets.get("call"):
        add("warn", "assets", "no call asset; lead and call businesses should show their phone number")
    monthly = num(econ.get("monthly_budget"))
    if monthly and total_daily and abs(total_daily * DAYS_PER_MONTH - monthly) > 0.1 * monthly:
        add("warn", "budget", f"campaign daily budgets add up to {total_daily * DAYS_PER_MONTH:,.0f}/month, "
                              f"but the plan says {monthly:,.0f}/month")
    return out


def cmd_blueprint(a):
    bp = read_json(a.file)
    if a.action == "check":
        issues = check_blueprint(bp)
        errors = [i for i in issues if i[0] == "error"]
        for level, where, msg in issues:
            print(f"{level.upper():5} {where}: {msg}")
        n_kw = sum(len(gr.get("keywords", [])) for c in bp.get("campaigns", []) for gr in c.get("ad_groups", []))
        print(f"\n{len(bp.get('campaigns', []))} campaigns, "
              f"{sum(len(c.get('ad_groups', [])) for c in bp.get('campaigns', []))} ad groups, {n_kw} keywords. "
              f"{len(errors)} errors, {len(issues) - len(errors)} warnings.")
        sys.exit(1 if errors else 0)
    md = render_blueprint(bp)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"Wrote {a.out}")
    else:
        print(md)


def kw_notation(text, match):
    return f"[{text}]" if match == "EXACT" else f'"{text}"' if match == "PHRASE" else text


def render_blueprint(bp):
    cur = bp.get("currency", "")
    econ = bp.get("economics") or {}
    geo = bp.get("geo") or {}
    L = [f"# Google Ads build sheet: {bp.get('business', '')}", ""]
    L.append(f"Goal: {bp.get('goal', '')}. Monthly budget: {num(econ.get('monthly_budget')):,.0f} {cur}. "
             f"Break-even cost per {'lead' if bp.get('goal') in ('leads', 'calls') else 'sale'}: "
             f"{num(econ.get('break_even_cpa')):,.0f} {cur}." if econ else f"Goal: {bp.get('goal', '')}.")
    L.append("")
    L.append("Build everything **paused**. Turn it on only after the conversion test in step 1 passes.")
    L += ["", "## 1. Conversion tracking (do this first)", ""]
    for c in (bp.get("conversions") or {}).get("primary", []):
        L.append(f"- **Primary:** {c.get('name')} ({c.get('category', '')}, count {c.get('counting', 'ONE')}"
                 f"{', value ' + str(c.get('value')) if c.get('value') else ''}). {c.get('how', '')}".rstrip())
    for c in (bp.get("conversions") or {}).get("secondary", []):
        L.append(f"- Secondary (observe only): {c.get('name')}. {c.get('how', '')}".rstrip())
    L.append("- Test it: submit a real test lead or order, then check Goals > Conversions shows it within a day.")
    L += ["", "## 2. Account settings", ""]
    L.append(f"- Locations: {', '.join(str(x) for x in geo.get('locations', []))}. "
             f"Location option: presence (people in or regularly in these places).")
    if geo.get("exclude"):
        L.append(f"- Exclude: {', '.join(geo['exclude'])}")
    if bp.get("schedule"):
        L.append(f"- Ad schedule: {bp['schedule']}")
    L.append("- Auto-tagging on. Link Google Analytics 4 if the site has it.")
    negs = (bp.get("negatives") or {}).get("account", [])
    if negs:
        L += ["", "## 3. Shared negative keyword list", "",
              "Create one list (Tools > Shared library > Negative keyword lists) and apply it to every Search campaign:", "",
              "```", *[kw_notation(*parse_kw(n)) for n in negs], "```"]
    L += ["", "## 4. Campaigns", ""]
    for camp in bp.get("campaigns", []):
        nets = camp.get("networks") or {}
        L.append(f"### {camp.get('name')}")
        L.append("")
        L.append(f"- Type: {camp.get('type', 'SEARCH')}. Daily budget: {num(camp.get('budget_daily')):,.2f} {cur}. "
                 f"Bidding: {camp.get('bidding', '')}"
                 f"{' (target ' + str(camp.get('target_cpa')) + ')' if camp.get('target_cpa') else ''}.")
        L.append(f"- Networks: Search Partners {'on' if nets.get('search_partners') else 'off'}, "
                 f"Display {'on' if nets.get('display') else 'off'}.")
        if camp.get("why"):
            L.append(f"- Why: {camp['why']}")
        if camp.get("negatives"):
            L += ["- Campaign negatives:", "", "```", *[kw_notation(*parse_kw(n)) for n in camp["negatives"]], "```"]
        for grp in camp.get("ad_groups", []):
            L += ["", f"#### Ad group: {grp.get('name')}", "", f"Landing page: {grp.get('landing_page', '')}", "",
                  "Keywords (paste as-is; the brackets and quotes set the match type):", "", "```"]
            L += [kw_notation(*parse_kw(k)) for k in grp.get("keywords", [])]
            L.append("```")
            for ai, ad in enumerate(grp.get("ads", [])):
                L += ["", f"Responsive search ad {ai + 1}" +
                      (f" (display path /{ad.get('path1', '')}/{ad.get('path2', '')})" if ad.get("path1") else ""), "",
                      "| # | Headline | Chars |", "|---|---|---|"]
                L += [f"| {i + 1} | {h} | {len(h)} |" for i, h in enumerate(ad.get("headlines", []))]
                L += ["", "| # | Description | Chars |", "|---|---|---|"]
                L += [f"| {i + 1} | {d} | {len(d)} |" for i, d in enumerate(ad.get("descriptions", []))]
        L.append("")
    assets = bp.get("assets") or {}
    if assets:
        L += ["## 5. Assets (account level unless a campaign needs its own)", ""]
        for s in assets.get("sitelinks", []):
            L.append(f"- Sitelink: **{s.get('text')}** ({s.get('url')}) {s.get('desc1', '')} / {s.get('desc2', '')}")
        if assets.get("callouts"):
            L.append(f"- Callouts: {', '.join(assets['callouts'])}")
        for sn in assets.get("snippets", []):
            L.append(f"- Structured snippet ({sn.get('header')}): {', '.join(sn.get('values', []))}")
        if assets.get("call"):
            L.append(f"- Call asset: {assets['call']}")
        L.append("")
    L += ["## 6. Launch checklist", "",
          "- [ ] Test conversion recorded", "- [ ] Every campaign: locations set, presence only, networks as above",
          "- [ ] Shared negative list applied to every Search campaign", "- [ ] Ads approved (no disapprovals)",
          "- [ ] Budgets and bidding match this sheet", "- [ ] Turn campaigns on",
          "- [ ] Day 7: first search-terms review. Day 30: run the Google Ads audit.", ""]
    if bp.get("phases"):
        L += ["## Later phases", ""] + [f"- {p}" for p in bp["phases"]] + [""]
    return "\n".join(L)


# ---------- fetch ----------

def audit_queries(start, end, history_start):
    D = f"segments.date BETWEEN '{start}' AND '{end}'"
    return {
        "account": "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, "
                   "customer.auto_tagging_enabled, customer.status FROM customer",
        "history": f"SELECT segments.month, metrics.cost_micros, metrics.conversions FROM customer "
                   f"WHERE segments.date BETWEEN '{history_start}' AND '{end}'",
        "campaigns": "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
                     "campaign.bidding_strategy_type, campaign_budget.resource_name, campaign_budget.amount_micros, "
                     "campaign_budget.explicitly_shared, campaign.network_settings.target_search_network, "
                     "campaign.network_settings.target_content_network, "
                     "campaign.network_settings.target_partner_search_network, "
                     "campaign.geo_target_type_setting.positive_geo_target_type, campaign.target_cpa.target_cpa_micros, "
                     "campaign.maximize_conversions.target_cpa_micros, campaign.target_roas.target_roas, "
                     "campaign.maximize_conversion_value.target_roas, metrics.cost_micros, metrics.conversions, "
                     "metrics.conversions_value, metrics.clicks, metrics.impressions, metrics.search_impression_share, "
                     "metrics.search_budget_lost_impression_share, metrics.search_rank_lost_impression_share "
                     f"FROM campaign WHERE campaign.status != 'REMOVED' AND {D}",
        "keywords": "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, ad_group.status, campaign.status, "
                    "ad_group_criterion.criterion_id, ad_group_criterion.keyword.text, "
                    "ad_group_criterion.keyword.match_type, ad_group_criterion.status, ad_group_criterion.negative, "
                    "ad_group_criterion.approval_status, ad_group_criterion.quality_info.quality_score, "
                    "ad_group_criterion.quality_info.creative_quality_score, "
                    "ad_group_criterion.quality_info.post_click_quality_score, "
                    "ad_group_criterion.quality_info.search_predicted_ctr, metrics.cost_micros, metrics.conversions, "
                    "metrics.clicks, metrics.impressions FROM keyword_view "
                    "WHERE ad_group_criterion.status != 'REMOVED' AND campaign.status != 'REMOVED' "
                    f"AND ad_group.status != 'REMOVED' AND {D}",
        "keywords_all": "SELECT campaign.id, campaign.name, campaign.status, ad_group.id, ad_group.name, ad_group.status, "
                        "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, "
                        "ad_group_criterion.status, ad_group_criterion.negative FROM ad_group_criterion "
                        "WHERE ad_group_criterion.type = 'KEYWORD' AND ad_group_criterion.status != 'REMOVED' "
                        "AND campaign.status != 'REMOVED' AND ad_group.status != 'REMOVED'",
        "search_terms": "SELECT campaign.id, campaign.name, ad_group.name, search_term_view.search_term, "
                        "search_term_view.status, metrics.cost_micros, metrics.conversions, metrics.clicks, "
                        f"metrics.impressions FROM search_term_view WHERE {D} "
                        "ORDER BY metrics.cost_micros DESC LIMIT 10000",
        "ads": "SELECT campaign.id, campaign.name, campaign.status, ad_group.id, ad_group.name, ad_group.status, "
               "ad_group_ad.ad.id, ad_group_ad.ad.type, ad_group_ad.status, ad_group_ad.ad_strength, "
               "ad_group_ad.policy_summary.approval_status, ad_group_ad.ad.final_urls, "
               "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions "
               "FROM ad_group_ad WHERE ad_group_ad.status != 'REMOVED' AND campaign.status != 'REMOVED' "
               "AND ad_group.status != 'REMOVED'",
        "ad_metrics": f"SELECT ad_group_ad.ad.id, metrics.cost_micros, metrics.impressions, metrics.conversions "
                      f"FROM ad_group_ad WHERE ad_group_ad.status != 'REMOVED' AND {D}",
        "campaign_assets": "SELECT campaign.id, campaign_asset.field_type, campaign_asset.status, asset.type "
                           "FROM campaign_asset WHERE campaign_asset.status = 'ENABLED'",
        "customer_assets": "SELECT customer_asset.field_type, customer_asset.status, asset.type FROM customer_asset "
                           "WHERE customer_asset.status = 'ENABLED'",
        "conversion_actions": "SELECT conversion_action.id, conversion_action.name, conversion_action.status, "
                              "conversion_action.type, conversion_action.category, conversion_action.primary_for_goal, "
                              "conversion_action.counting_type, conversion_action.include_in_conversions_metric, "
                              "conversion_action.attribution_model_settings.attribution_model, "
                              "conversion_action.click_through_lookback_window_days, "
                              "conversion_action.value_settings.default_value, "
                              "conversion_action.value_settings.always_use_default_value, conversion_action.origin "
                              "FROM conversion_action WHERE conversion_action.status = 'ENABLED'",
        "conversions_by_action": f"SELECT segments.conversion_action_name, metrics.all_conversions, metrics.conversions "
                                 f"FROM customer WHERE {D}",
        "campaign_criteria": "SELECT campaign.id, campaign_criterion.type, campaign_criterion.negative, "
                             "campaign_criterion.status FROM campaign_criterion WHERE campaign.status != 'REMOVED' "
                             "AND campaign_criterion.type IN ('KEYWORD', 'LOCATION', 'AD_SCHEDULE', 'USER_LIST', "
                             "'PROXIMITY', 'LANGUAGE')",
        "shared_sets": "SELECT shared_set.id, shared_set.name, shared_set.type, shared_set.member_count, "
                       "shared_set.status FROM shared_set WHERE shared_set.status = 'ENABLED'",
        "campaign_shared_sets": "SELECT campaign.id, shared_set.id, shared_set.type, campaign_shared_set.status "
                                "FROM campaign_shared_set WHERE campaign_shared_set.status = 'ENABLED'",
        "user_lists": "SELECT user_list.id, user_list.name, user_list.type, user_list.size_for_search, "
                      "user_list.membership_status FROM user_list",
        "asset_groups": "SELECT campaign.id, campaign.status, asset_group.id, asset_group.name, asset_group.status, "
                        f"asset_group.ad_strength, metrics.cost_micros, metrics.conversions FROM asset_group "
                        f"WHERE asset_group.status != 'REMOVED' AND {D}",
        "change_events": "SELECT change_event.change_date_time, change_event.change_resource_type, "
                         "change_event.resource_change_operation, change_event.changed_fields, change_event.campaign "
                         "FROM change_event WHERE change_event.change_date_time DURING LAST_14_DAYS "
                         "ORDER BY change_event.change_date_time DESC LIMIT 10000",
    }


def cmd_fetch(a):
    acct = load_account(a.business, a.customer, a.login)
    cid, login = acct["customer_id"], acct.get("login_customer_id")
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=a.days - 1)
    hist = (end.replace(day=1) - dt.timedelta(days=740)).replace(day=1)
    folder = out_dir(a.business) / "data" / f"{dt.date.today()}-{cid}"
    folder.mkdir(parents=True, exist_ok=True)
    failures = {}
    for name, q in audit_queries(start, end, hist).items():
        try:
            rows = search(cid, q, login)
            write_json(folder / f"{name}.json", {"results": rows})
            print(f"ok     {name:22} {len(rows):>6} rows")
        except ApiError as e:
            failures[name] = str(e)
            print(f"FAILED {name:22} {e}")
    write_json(folder / "manifest.json", {"customer_id": cid, "name": acct.get("name", ""),
                                          "currency": acct.get("currency", ""), "days": a.days,
                                          "start": str(start), "end": str(end), "api_version": _version[0],
                                          "fetched": dt.datetime.now().isoformat(timespec="seconds"),
                                          "failures": failures})
    print(f"\nSaved to {folder}")
    if failures:
        print(f"{len(failures)} queries failed; the audit will mark what they feed as not measured.")
        sys.exit(1 if len(failures) == len(audit_queries(start, end, hist)) else 0)


# ---------- audit ----------

class Audit:
    def __init__(self, folder, goal=None, target_cpa=None, target_roas=None, brand=None, answers=None):
        self.folder = Path(folder)
        mf = self.folder / "manifest.json"
        self.manifest = read_json(mf) if mf.exists() else {}
        self.days = self.manifest.get("days", 30)
        self.scale = DAYS_PER_MONTH / self.days
        self.cur = self.manifest.get("currency", "")
        self.failures = self.manifest.get("failures", {})
        self.brand = [b.lower() for b in (brand or []) if b.strip()]
        self.answers = answers or {}
        self.target_cpa, self.target_roas = target_cpa, target_roas
        self.signals, self.asks = [], []
        self.d = {}
        for f in self.folder.glob("*.json"):
            if f.name not in ("manifest.json", "audit.json"):
                self.d[f.stem] = read_json(f).get("results", [])
        self.camps = {}
        for r in self.d.get("campaigns", []):
            c = r["campaign"]
            m = r.get("metrics", {})
            self.camps[c["id"]] = {
                "id": c["id"], "name": c.get("name", ""), "status": c.get("status"),
                "type": c.get("advertisingChannelType"), "bidding": c.get("biddingStrategyType"),
                "cost": micros(m.get("costMicros")), "conv": num(m.get("conversions")),
                "value": num(m.get("conversionsValue")), "clicks": num(m.get("clicks")),
                "impr": num(m.get("impressions")),
                "is": num(m.get("searchImpressionShare"), None),
                "lost_budget": num(m.get("searchBudgetLostImpressionShare"), None),
                "lost_rank": num(m.get("searchRankLostImpressionShare"), None),
                "budget": micros(g(r, "campaignBudget", "amountMicros")),
                "budget_rn": g(r, "campaignBudget", "resourceName"),
                "shared": bool(g(r, "campaignBudget", "explicitlyShared")),
                "display": bool(g(c, "networkSettings", "targetContentNetwork")),
                "partners": bool(g(c, "networkSettings", "targetPartnerSearchNetwork")),
                "geo_type": g(c, "geoTargetTypeSetting", "positiveGeoTargetType"),
                "tcpa": micros(g(c, "targetCpa", "targetCpaMicros") or g(c, "maximizeConversions", "targetCpaMicros")) or None,
                "troas": num(g(c, "targetRoas", "targetRoas") or g(c, "maximizeConversionValue", "targetRoas"), None) or None,
            }
        self.enabled = [c for c in self.camps.values() if c["status"] == "ENABLED"]
        self.paused_spend = [c for c in self.camps.values() if c["status"] != "ENABLED" and c["cost"] > 0]
        self.search = [c for c in self.enabled if c["type"] == "SEARCH"]
        self.spend = sum(c["cost"] for c in self.camps.values())
        self.conv = sum(c["conv"] for c in self.camps.values())
        self.value = sum(c["value"] for c in self.camps.values())
        self.cpa = self.spend / self.conv if self.conv else None
        self.goal = goal or self.deduce_goal()

    # helpers
    def has(self, *names):
        return all(n in self.d and n not in self.failures for n in names)

    def money(self, v):
        return f"{v:,.0f} {self.cur}".strip()

    def monthly(self, v):
        return v * self.scale

    def add(self, cat, sid, name, status, evidence, fix="", impact=None):
        self.signals.append({"category": cat, "id": sid, "name": name, "status": status, "evidence": evidence,
                             "fix": fix, "monthly_impact": round(impact, 2) if impact else None})

    def ask(self, cat, sid, name, key, question, fix):
        ans = str(self.answers.get(key, "")).strip().lower()
        if ans in ("yes", "true", "pass", "y"):
            self.add(cat, sid, name, "PASS", f"Owner confirmed: {question}")
        elif ans in ("partial", "some", "warn"):
            self.add(cat, sid, name, "WARN", f"Owner said partly: {question}", fix)
        elif ans in ("no", "false", "fail", "n"):
            self.add(cat, sid, name, "FAIL", f"Owner said no: {question}", fix)
        elif ans in ("na", "n/a", "not applicable"):
            self.add(cat, sid, name, "NA", "Owner said not applicable.")
        else:
            self.add(cat, sid, name, "ASK", question, fix)
            self.asks.append({"key": key, "question": question})

    def unmeasured(self, cat, sid, name, needs):
        missing = [n for n in needs if n not in self.d or n in self.failures]
        self.add(cat, sid, name, "UNKNOWN", f"Not measured: data for {', '.join(missing)} didn't load.")

    def deduce_goal(self):
        types = {c["type"] for c in self.enabled}
        if types & {"SHOPPING"} or (self.value > 0 and types & {"PERFORMANCE_MAX"}):
            return "sales"
        if self.value > 0 and self.conv and self.value / self.conv > 1.5:
            return "sales"
        if self.conv > 0:
            return "leads"
        return "unknown"

    def maturity(self):
        months = sorted((g(r, "segments", "month"), micros(g(r, "metrics", "costMicros")))
                        for r in self.d.get("history", []))
        spent = [m for m, c in months if c > 0]
        if not spent:
            return "new", None
        first = dt.date.fromisoformat(spent[0])
        age = (dt.date.today() - first).days / 30.4
        return ("mature" if age >= 24 else "established" if age >= 6 else "new"), spent[0]

    def is_brand(self, text):
        t = text.lower()
        return bool(self.brand) and any(b in t for b in self.brand)

    # the categories
    def run(self):
        self.c1_account()
        self.c2_conversions()
        self.c3_structure()
        self.c4_pmax()
        self.c5_budgets()
        self.c6_bidding()
        self.c7_targeting()
        self.c8_audiences()
        self.c9_keywords()
        self.c10_quality()
        self.c11_search_terms()
        self.c12_ads()
        self.c13_assets()
        self.c14_landing()
        return self

    def c1_account(self):
        if self.has("shared_sets", "campaign_shared_sets") and self.search:
            neg = {g(r, "sharedSet", "id") for r in self.d["shared_sets"] if g(r, "sharedSet", "type") == "NEGATIVE_KEYWORDS"}
            covered = {g(r, "campaign", "id") for r in self.d["campaign_shared_sets"] if g(r, "sharedSet", "id") in neg}
            # Brand campaigns are exempt: a generic list can block brand searches.
            need = [c for c in self.search if not ("brand" in c["name"].lower() and "non" not in c["name"].lower())]
            if not need:
                self.add(1, "1.1", "Shared negative keyword list on Search campaigns", "NA",
                         "Only brand Search campaigns are live; they don't need the shared list.")
            else:
                n = sum(1 for c in need if c["id"] in covered)
                share = n / len(need)
                st = "PASS" if share >= 0.8 else "WARN" if n else "FAIL"
                self.add(1, "1.1", "Shared negative keyword list on Search campaigns", st,
                         f"{len(neg)} shared negative list(s); applied to {n} of {len(need)} enabled non-brand Search campaigns.",
                         "Create one shared negative list and apply it to every non-brand Search campaign.")
        elif not self.search:
            self.add(1, "1.1", "Shared negative keyword list on Search campaigns", "NA", "No enabled Search campaigns.")
        else:
            self.unmeasured(1, "1.1", "Shared negative keyword list on Search campaigns", ["shared_sets", "campaign_shared_sets"])
        acct = (self.d.get("account") or [{}])[0].get("customer", {})
        if acct:
            on = acct.get("autoTaggingEnabled")
            self.add(1, "1.2", "Auto-tagging on", "PASS" if on else "FAIL",
                     f"Auto-tagging is {'on' if on else 'off'}.",
                     "Turn on auto-tagging (Admin > Account settings). Without it Analytics and offline imports can't tie leads to clicks.")
            ps = sum(c["cost"] for c in self.paused_spend)
            self.add(1, "1.4", "What is live now", "INFO",
                     f"{len(self.enabled)} enabled campaign(s): {', '.join(c['name'] + ' (' + c['type'] + ')' for c in self.enabled[:6])}. "
                     + (f"{ps / self.spend:.0%} of the period's spend ({self.money(ps)}) was in campaigns now paused: "
                        f"{', '.join(c['name'] for c in self.paused_spend[:5])}. Checks on settings look at live campaigns only."
                        if ps and self.spend else "No spend in paused campaigns."))
            self.add(1, "1.3", "Time zone and currency", "INFO",
                     f"Time zone {acct.get('timeZone')}, currency {acct.get('currencyCode')}. Neither can be changed later; "
                     "confirm they match the business.")

    def c2_conversions(self):
        if not self.has("conversion_actions"):
            return self.unmeasured(2, "2.1", "Primary conversion actions", ["conversion_actions"])
        acts = [r["conversionAction"] for r in self.d["conversion_actions"]]
        # "Primary" that bidding and the Conversions column actually use = included in conversions.
        prim = [x for x in acts if x.get("primaryForGoal") and x.get("includeInConversionsMetric")]
        micro = [x for x in prim if x.get("category") in MICRO_CATEGORIES]
        names = ", ".join(f"{x.get('name')} ({x.get('category')})" for x in prim[:8])
        if not prim:
            st, ev = "FAIL", "No primary conversion actions. Smart bidding has nothing to aim at."
        elif micro and self.goal in ("leads", "sales", "calls"):
            st, ev = "FAIL", f"Micro-events counted as primary: {', '.join(x.get('name') for x in micro)}. Primary: {names}."
        elif self.goal == "sales" and [x for x in prim if x.get("category") != "PURCHASE"]:
            off = [x.get("name") for x in prim if x.get("category") != "PURCHASE"]
            st, ev = "WARN", (f"An online store counting non-sales actions as primary conversions: {', '.join(off[:6])}. "
                              f"Primary: {names}.")
        elif len(prim) > 5:
            st, ev = "WARN", f"{len(prim)} primary actions; bidding spreads thin. Primary: {names}."
        else:
            st, ev = "PASS", f"{len(prim)} primary action(s): {names}."
        self.add(2, "2.1", "Primary conversions are real business outcomes", st, ev,
                 "Keep 1-3 primary actions that are real outcomes (lead, booked call, purchase). Make the rest secondary.")
        if self.spend > 0:
            st = "PASS" if self.conv > 0 else "FAIL"
            by = [f"{g(r, 'segments', 'conversionActionName')}: {num(g(r, 'metrics', 'allConversions')):.0f}"
                  for r in self.d.get("conversions_by_action", [])][:8]
            self.add(2, "2.2", "Conversions are being recorded", st,
                     f"{self.conv:,.1f} conversions on {self.money(self.spend)} spend in {self.days} days. "
                     f"By action (all conversions): {', '.join(by) or 'none'}.",
                     "Send a test lead or order and confirm it shows up. If it doesn't, the tag or import is broken: fix before anything else.")
        lead_many = [x for x in prim if x.get("category") in LEAD_CATEGORIES and x.get("countingType") == "MANY_PER_CLICK"]
        buy_one = [x for x in prim if x.get("category") == "PURCHASE" and x.get("countingType") == "ONE_PER_CLICK"]
        if prim:
            bad = lead_many + buy_one
            self.add(2, "2.3", "Counting method fits the action", "WARN" if bad else "PASS",
                     ("Leads counted every time: " + ", ".join(x.get("name") for x in lead_many) + ". " if lead_many else "") +
                     ("Purchases counted once per click: " + ", ".join(x.get("name") for x in buy_one) + "." if buy_one else "") or
                     "Lead actions count one per click; purchases count every one.",
                     "Leads: count 'One'. Purchases: count 'Every'.")
            by_cat = {}
            for x in prim:
                if x.get("category") not in MICRO_CATEGORIES:
                    by_cat.setdefault(x.get("category"), []).append(x)
            dup = {k: v for k, v in by_cat.items() if len(v) > 1 and len({y.get("type") for y in v}) > 1}
            self.add(2, "2.4", "No double counting", "WARN" if dup else "PASS",
                     "; ".join(f"{k}: {', '.join(y.get('name') + ' [' + str(y.get('type')) + ']' for y in v)}" for k, v in dup.items())
                     or "No category has two primary actions from different sources.",
                     "When the same outcome is tracked two ways (e.g. a Google Ads tag and a GA4 import), keep one primary and make the other secondary.")
        if self.goal == "sales":
            st = "PASS" if self.value > 0 else "FAIL"
            self.add(2, "2.5", "Conversion values flow", st,
                     f"Conversion value {self.money(self.value)} in {self.days} days.",
                     "Pass the order value with each purchase so bidding can aim at revenue.")
        elif self.goal in ("leads", "calls"):
            has_value = self.value > self.conv * 1.01 if self.conv else False
            self.add(2, "2.5", "Leads carry a value", "PASS" if has_value else "WARN",
                     f"Conversion value {self.money(self.value)} for {self.conv:,.0f} conversions.",
                     "Give each lead type a value (what a lead is worth on average) so bidding prefers the better ones.")
            offline = [x for x in acts if x.get("type") == "UPLOAD_CLICKS" or x.get("category") in ("QUALIFIED_LEAD", "CONVERTED_LEAD")]
            self.add(2, "2.6", "Real sales results fed back to Google", "PASS" if offline else "WARN",
                     f"{len(offline)} offline/CRM conversion action(s)." if offline else
                     "No offline or CRM conversion import. Google only sees form fills, not which ones became customers.",
                     "Import qualified leads and closed deals from the CRM (offline conversion import). It is the biggest lever for lead quality.")
        self.ask(2, "2.7", "Enhanced conversions", "enhanced_conversions",
                 "Is enhanced conversions turned on for your main conversion (Goals > Settings)?",
                 "Turn on enhanced conversions so hashed email/phone from the form improves measurement.")
        self.ask(2, "2.8", "Consent mode (EU/EEA/UK visitors only)", "consent_mode",
                 "Do you advertise to people in the EU, EEA or UK? If yes, is Google consent mode set up on the site? (Answer n/a if you don't.)",
                 "Set up consent mode v2 through your cookie banner; without it EU conversions go missing.")

    def c3_structure(self):
        if not self.brand:
            self.add(3, "3.1", "Brand and non-brand separated", "ASK",
                     "What is your brand name (and common misspellings)? Needed to check brand vs non-brand.",
                     "Keep brand keywords in their own campaign with their own budget.")
            self.asks.append({"key": "brand_terms", "question": "What is your brand name, and any common misspellings?"})
        elif self.has("keywords_all"):
            per = {}
            for r in self.d["keywords_all"]:
                if g(r, "adGroupCriterion", "negative") or g(r, "adGroupCriterion", "status") != "ENABLED":
                    continue
                if g(r, "campaign", "status") != "ENABLED":
                    continue
                cid = g(r, "campaign", "id")
                b = self.is_brand(g(r, "adGroupCriterion", "keyword", "text", default=""))
                per.setdefault(cid, [0, 0])[0 if b else 1] += 1
            mixed = [self.camps[c]["name"] for c, (b, nb) in per.items() if b and nb and b / (b + nb) < 0.8 and c in self.camps]
            has_brand = any(b for b, _ in per.values())
            st = "FAIL" if mixed else "PASS" if has_brand else "WARN"
            self.add(3, "3.1", "Brand and non-brand separated", st,
                     f"Campaigns mixing brand and non-brand keywords: {', '.join(mixed)}." if mixed else
                     "Brand keywords sit in their own campaign(s)." if has_brand else
                     "No brand keywords found. Competitors can take your brand searches.",
                     "Brand keywords in one Brand campaign with its own small budget; add the brand name as a negative everywhere else.")
        if self.enabled and self.spend:
            share = {}
            for c in self.camps.values():
                share[c["type"]] = share.get(c["type"], 0) + c["cost"]
            mix = ", ".join(f"{k} {v / self.spend:.0%}" for k, v in sorted(share.items(), key=lambda x: -x[1]) if v)
            live_types = {c["type"] for c in self.enabled}
            st, why = "PASS", ""
            if self.goal == "sales" and not {"SHOPPING", "PERFORMANCE_MAX"} & live_types:
                paused = [c["name"] for c in self.paused_spend if c["type"] in ("SHOPPING", "PERFORMANCE_MAX")]
                st, why = "FAIL", ("An online store with no live Shopping or Performance Max campaign"
                                   + (f" (paused during the period: {', '.join(paused)})." if paused else "."))
            elif self.goal in ("leads", "calls") and share.get("PERFORMANCE_MAX", 0) / self.spend > 0.7:
                st, why = "WARN", "Performance Max takes most of a lead-gen budget; Search should be the anchor."
            elif (share.get("DISPLAY", 0) + share.get("VIDEO", 0) + share.get("DEMAND_GEN", 0)) / self.spend > 0.5 \
                    and self.goal in ("leads", "sales", "calls"):
                st, why = "WARN", "Awareness channels take most of the spend on a results account."
            self.add(3, "3.2", "Campaign types fit the goal", st, f"Goal: {self.goal}. Period spend mix: {mix}. {why}".strip(),
                     "Anchor lead-gen on Search; stores on Shopping/Performance Max plus brand Search.")
        starved = [c for c in self.search if c["cost"] > 0 and self.monthly(c["conv"]) < SMART_BIDDING_MIN
                   and c["bidding"] not in NON_SMART]
        if self.search:
            self.add(3, "3.3", "Campaigns have enough data each", "WARN" if len(starved) >= 2 else "PASS",
                     f"{len(starved)} smart-bidding Search campaigns under {SMART_BIDDING_MIN} conversions/month: "
                     f"{', '.join(c['name'] for c in starved[:6])}." if len(starved) >= 2 else
                     "No split-up campaigns starving smart bidding.",
                     "Merge thin campaigns that share a goal and geography so each one feeds bidding enough conversions.")

    def c4_pmax(self):
        pmax = [c for c in self.enabled if c["type"] == "PERFORMANCE_MAX"]
        if not pmax:
            self.add(4, "4.1", "Performance Max asset groups strong", "NA", "No enabled Performance Max campaigns.")
        elif self.has("asset_groups"):
            ids = {c["id"] for c in pmax}
            ags = [r["assetGroup"] for r in self.d["asset_groups"]
                   if g(r, "campaign", "id") in ids and g(r, "assetGroup", "status") == "ENABLED"]
            rated = [x for x in ags if x.get("adStrength") in ("POOR", "AVERAGE", "GOOD", "EXCELLENT")]
            good = [x for x in rated if x.get("adStrength") in ("GOOD", "EXCELLENT")]
            share = len(good) / len(rated) if rated else None
            st = "NA" if share is None else "PASS" if share >= 0.8 else "WARN" if share >= 0.5 else "FAIL"
            self.add(4, "4.1", "Performance Max asset groups strong", st,
                     f"{len(good)} of {len(rated)} enabled asset groups rated Good/Excellent.",
                     "Fill each asset group: 15 images, 5 videos, 5 headlines, 5 long headlines, 5 descriptions, plus audience signals and search themes.")
        else:
            self.unmeasured(4, "4.1", "Performance Max asset groups strong", ["asset_groups"])
        if pmax:
            self.ask(4, "4.2", "Performance Max brand exclusions", "pmax_brand_exclusions",
                     "Do your Performance Max campaigns exclude your brand name (brand exclusions)?",
                     "Add brand exclusions to Performance Max so it can't take credit for people already searching your name.")
        visual = [c for c in self.enabled if c["type"] in ("DISPLAY", "PERFORMANCE_MAX", "DEMAND_GEN")]
        if visual:
            self.ask(4, "4.3", "Placement exclusions", "placement_exclusions",
                     "Is there a placement exclusion list (e.g. mobile apps, games, parked domains) on Display, Demand Gen or Performance Max?",
                     "Exclude low-quality placements (mobile app categories, parked domains) account-wide.")

    def c5_budgets(self):
        if not self.search:
            return self.add(5, "5.1", "Profitable campaigns not held back by budget", "NA", "No enabled Search campaigns.")
        bar = self.target_cpa or self.cpa
        eff = [c for c in self.search if c["conv"] >= 3 and c["lost_budget"] is not None
               and (bar is None or c["cost"] / c["conv"] <= bar)]
        if eff:
            worst = max(eff, key=lambda c: c["lost_budget"])
            lb = worst["lost_budget"]
            st = "PASS" if lb < 0.10 else "WARN" if lb <= 0.25 else "FAIL"
            self.add(5, "5.1", "Profitable campaigns not held back by budget", st,
                     "; ".join(f"{c['name']}: {c['lost_budget']:.0%} of searches missed for budget, CPA "
                               f"{self.money(c['cost'] / c['conv'])}" for c in sorted(eff, key=lambda c: -c["lost_budget"])[:5]),
                     "Move budget from the wasteful spend found below into campaigns that convert at or under target and are losing impressions to budget.")
        else:
            self.add(5, "5.1", "Profitable campaigns not held back by budget", "NA",
                     "No Search campaign has enough conversions at or under the target to judge.")
        shared = {}
        for c in self.enabled:
            if c["shared"]:
                shared.setdefault(c["budget_rn"], []).append(c)
        if shared:
            worst = max(len(v) for v in shared.values())
            brand_in = any(any("brand" in c["name"].lower() for c in v) and len(v) > 1 for v in shared.values())
            st = "FAIL" if worst >= 5 or brand_in else "WARN" if worst >= 3 else "PASS"
            self.add(5, "5.2", "Shared budgets don't starve campaigns", st,
                     "; ".join(f"{len(v)} campaigns share one budget: {', '.join(c['name'] for c in v[:5])}" for v in shared.values()),
                     "Give brand its own budget and group only campaigns with similar goals in a shared budget.")
        else:
            self.add(5, "5.2", "Shared budgets don't starve campaigns", "PASS", "No shared budgets.")
        bar = max(3 * (self.target_cpa or self.cpa or 0), 0.05 * self.spend) if self.spend else 0
        dead = [c for c in self.enabled if c["conv"] == 0 and c["cost"] >= bar and c["cost"] > 0]
        cost = sum(c["cost"] for c in dead)
        self.add(5, "5.3", "No campaign spending without results", "FAIL" if dead else "PASS",
                 f"Zero conversions: {', '.join(c['name'] + ' ' + self.money(c['cost']) for c in dead)}." if dead else
                 "Every campaign with real spend has conversions.",
                 "Find why (tracking, targeting, offer, landing page) before adding budget; pause if nothing is found.",
                 self.monthly(cost) if dead else None)

    def c6_bidding(self):
        if not self.search:
            return
        mis = [c for c in self.search if c["bidding"] == "ENHANCED_CPC" or
               (c["bidding"] in NON_SMART and self.monthly(c["conv"]) >= SMART_BIDDING_MIN)]
        sc = sum(c["cost"] for c in self.search) or 1
        share = sum(c["cost"] for c in mis) / sc
        st = "PASS" if share < 0.10 else "WARN" if share <= 0.5 else "FAIL"
        self.add(6, "6.1", "Bid strategy fits the data", st,
                 f"{share:.0%} of Search spend on manual/click bidding despite enough conversions for smart bidding"
                 f"{': ' + ', '.join(c['name'] + ' (' + c['bidding'] + ')' for c in mis[:5]) if mis else ''}. "
                 "Strategies: " + ", ".join(sorted({c['bidding'] for c in self.search})) + ".",
                 "15+ conversions/month: Maximize Conversions. 30+ steady: add a target CPA near your actual. Enhanced CPC is retired.")
        tgt = [c for c in self.search if c["bidding"] in TARGET_BIDS or c["tcpa"]]
        if tgt:
            low = min(self.monthly(c["conv"]) for c in tgt)
            st = "PASS" if low >= TARGET_BIDDING_MIN else "WARN" if low >= SMART_BIDDING_MIN else "FAIL"
            self.add(6, "6.2", "Targets have enough conversions behind them", st,
                     ", ".join(f"{c['name']}: {self.monthly(c['conv']):.0f}/month" for c in tgt[:6]),
                     "Below ~30 conversions/month a CPA or ROAS target is guesswork; drop the target or merge campaigns.")
            tight = [c for c in tgt if c["tcpa"] and c["conv"] and c["tcpa"] < 0.7 * (c["cost"] / c["conv"])]
            self.add(6, "6.3", "Targets are realistic", "WARN" if tight else "PASS",
                     "; ".join(f"{c['name']}: target {self.money(c['tcpa'])} vs actual {self.money(c['cost'] / c['conv'])}"
                               for c in tight) or "Targets sit near actual results.",
                     "Set the target at or slightly above the last 30 days' actual; move it 10-15% at a time, 1-2 weeks apart.")
        if self.has("change_events"):
            counts = {}
            for r in self.d["change_events"]:
                ev = r.get("changeEvent", {})
                if ev.get("changeResourceType") in ("CAMPAIGN", "CAMPAIGN_BUDGET", "BIDDING_STRATEGY"):
                    cid = str(ev.get("campaign", "")).split("/")[-1]
                    counts[cid] = counts.get(cid, 0) + 1
            busy = {self.camps[k]["name"]: v for k, v in counts.items() if k in self.camps and v >= 3}
            top = max(busy.values()) if busy else 0
            self.add(6, "6.4", "Bidding left alone long enough to learn", "PASS" if not busy else "WARN" if top <= 5 else "FAIL",
                     ", ".join(f"{k}: {v} changes" for k, v in busy.items()) + " in 14 days." if busy else
                     "Few campaign, budget or bidding changes in the last 14 days.",
                     "Batch changes and give smart bidding 1-2 weeks between them.")

    def c7_targeting(self):
        if not self.enabled:
            return
        poi = [c for c in self.enabled if c["geo_type"] == "PRESENCE_OR_INTEREST"]
        st = "PASS" if not poi else "WARN" if len(poi) < len(self.enabled) / 2 else "FAIL"
        self.add(7, "7.1", "Location option is 'presence'", st,
                 f"Presence-or-interest on: {', '.join(c['name'] for c in poi)}." if poi else
                 "All enabled campaigns target people in the area.",
                 "Location options: 'Presence: people in or regularly in your locations'.")
        disp = [c for c in self.search if c["display"]]
        part = [c for c in self.search if c["partners"]]
        st = "FAIL" if disp else "WARN" if part else "PASS"
        self.add(7, "7.2", "Search campaigns stay on Search", st,
                 (f"Display Network on: {', '.join(c['name'] for c in disp)}. " if disp else "") +
                 (f"Search Partners on: {', '.join(c['name'] for c in part)}." if part else "") or
                 "Search campaigns run on Google Search only.",
                 "Turn off the Display Network on Search campaigns; test Search Partners only once Search works.")
        if self.has("campaign_criteria"):
            crit = {}
            for r in self.d["campaign_criteria"]:
                cr = r.get("campaignCriterion", {})
                if cr.get("negative"):
                    continue
                crit.setdefault(g(r, "campaign", "id"), set()).add(cr.get("type"))
            nogeo = [c for c in self.enabled if c["type"] in ("SEARCH", "DISPLAY", "PERFORMANCE_MAX", "DEMAND_GEN")
                     and not crit.get(c["id"], set()) & {"LOCATION", "PROXIMITY"}]
            self.add(7, "7.3", "Every campaign has locations", "FAIL" if nogeo else "PASS",
                     f"No location targeting (shows worldwide): {', '.join(c['name'] for c in nogeo)}." if nogeo else
                     "Every campaign has location targeting.",
                     "Set locations on every campaign.")
            if self.goal in ("leads", "calls") and self.search:
                sched = [c for c in self.search if "AD_SCHEDULE" in crit.get(c["id"], set())]
                self.add(7, "7.4", "Ad schedule matches when leads get answered", "PASS" if sched else "WARN",
                         f"{len(sched)} of {len(self.search)} Search campaigns have an ad schedule.",
                         "If calls and forms are only answered in business hours, schedule ads for those hours "
                         "(or lower bids overnight) and check after 30 days.")

    def c8_audiences(self):
        if self.has("user_lists"):
            crm = [r["userList"] for r in self.d["user_lists"] if g(r, "userList", "type") == "CRM_BASED"]
            big = [x for x in crm if num(x.get("sizeForSearch")) >= 1000]
            st = "PASS" if big else "WARN"
            self.add(8, "8.1", "Customer list uploaded", st,
                     f"{len(crm)} customer list(s); {len(big)} big enough to use on Search (1,000+ matched)." if crm else
                     "No customer list (Customer Match).",
                     "Upload your customer list (Tools > Audience manager) and refresh it quarterly; use it to exclude customers and as a signal.")
        else:
            self.unmeasured(8, "8.1", "Customer list uploaded", ["user_lists"])
        if self.goal in ("leads", "calls"):
            self.ask(8, "8.2", "Existing customers excluded from prospecting", "exclude_customers",
                     "Are existing customers excluded from campaigns meant to find new ones?",
                     "Exclude your customer list from prospecting campaigns so you don't pay for people who already buy.")

    def c9_keywords(self):
        if not self.has("keywords_all"):
            return self.unmeasured(9, "9.1", "One home per keyword", ["keywords_all"])
        live = [r for r in self.d["keywords_all"] if not g(r, "adGroupCriterion", "negative")
                and g(r, "adGroupCriterion", "status") == "ENABLED" and g(r, "campaign", "status") == "ENABLED"
                and g(r, "adGroup", "status") == "ENABLED"]
        if not live:
            return self.add(9, "9.1", "One home per keyword", "NA", "No enabled keywords.")
        cost = {}
        for r in self.d.get("keywords", []):
            key = (g(r, "adGroupCriterion", "keyword", "text", default="").lower(), g(r, "adGroupCriterion", "keyword", "matchType"))
            cost[key] = cost.get(key, 0) + micros(g(r, "metrics", "costMicros"))
        homes = {}
        for r in live:
            key = (g(r, "adGroupCriterion", "keyword", "text", default="").lower(), g(r, "adGroupCriterion", "keyword", "matchType"))
            homes.setdefault(key, set()).add(g(r, "adGroup", "id"))
        dups = {k: v for k, v in homes.items() if len(v) > 1}
        dcost = sum(cost.get(k, 0) for k in dups)
        st = "PASS" if not dups else "WARN" if dcost < 0.01 * (self.spend or 1) else "FAIL"
        self.add(9, "9.1", "One home per keyword", st,
                 f"{len(dups)} keywords live in more than one ad group ({self.money(dcost)} spend)"
                 f"{': ' + ', '.join(repr(k[0]) for k in list(dups)[:6]) if dups else ''}." if dups else
                 "Each keyword and match type has one home.",
                 "Keep each keyword in the ad group that fits it best; remove the copies.")
        bid = {c["id"]: c["bidding"] for c in self.camps.values()}
        broad_manual = [r for r in live if g(r, "adGroupCriterion", "keyword", "matchType") == "BROAD"
                        and bid.get(g(r, "campaign", "id")) in NON_SMART]
        self.add(9, "9.2", "Broad match only with smart bidding", "FAIL" if broad_manual else "PASS",
                 f"{len(broad_manual)} broad keywords in manual/click-bid campaigns." if broad_manual else
                 "Broad match (if any) runs with smart bidding.",
                 "Broad match needs smart bidding, 30+ conversions/month and a solid negative list. Otherwise use phrase and exact.")
        if self.has("keywords"):
            kw = [r for r in self.d["keywords"] if not g(r, "adGroupCriterion", "negative")
                  and g(r, "adGroupCriterion", "status") == "ENABLED" and g(r, "campaign", "status", default="ENABLED") == "ENABLED"
                  and g(r, "adGroup", "status", default="ENABLED") == "ENABLED"]
            zero = [r for r in kw if num(g(r, "metrics", "impressions")) == 0]
            dis = [r for r in kw if g(r, "adGroupCriterion", "approvalStatus") == "DISAPPROVED"]
            share = len(zero) / len(kw) if kw else 0
            st = "FAIL" if dis else "WARN" if share > 0.05 else "PASS"
            self.add(9, "9.3", "No dead or disapproved keywords", st,
                     f"{len(zero)} of {len(kw)} enabled keywords had no impressions in {self.days} days; {len(dis)} disapproved.",
                     "Fix or remove disapproved keywords; pause keywords that never show after 30 days.")

    def c10_quality(self):
        if not self.has("keywords"):
            return self.unmeasured(10, "10.1", "Spend-weighted Quality Score", ["keywords"])
        rows = []
        for r in self.d["keywords"]:
            if g(r, "adGroupCriterion", "negative"):
                continue
            qs = g(r, "adGroupCriterion", "qualityInfo", "qualityScore")
            c = micros(g(r, "metrics", "costMicros"))
            if qs and c > 0:
                rows.append((num(qs), c, g(r, "adGroupCriterion", "qualityInfo", default={}),
                             g(r, "adGroupCriterion", "keyword", "text", default="")))
        if not rows:
            return self.add(10, "10.1", "Spend-weighted Quality Score", "NA", "No keywords with spend and a Quality Score.")
        tc = sum(c for _, c, _, _ in rows)
        wqs = sum(q * c for q, c, _, _ in rows) / tc
        st = "PASS" if wqs >= 7 else "WARN" if wqs >= 5 else "FAIL"
        self.add(10, "10.1", "Spend-weighted Quality Score", st, f"{wqs:.1f}/10 across {len(rows)} keywords with spend.",
                 "Work the lowest-scoring, highest-spend keywords first (see 10.3 for which part is weak).")
        low = sum(c for q, c, _, _ in rows if q <= 4)
        share = low / tc
        st = "PASS" if share < 0.10 else "WARN" if share <= 0.25 else "FAIL"
        self.add(10, "10.2", "Little spend on low Quality Score", st,
                 f"{share:.0%} of keyword spend ({self.money(low)}) on Quality Score 4 or below.",
                 "Tighter ad groups, the keyword in the headline, and a matching landing page lift the score and lower the click price.")
        top = sorted(rows, key=lambda x: -x[1])[:20]
        comps = {"searchPredictedCtr": "expected click rate", "creativeQualityScore": "ad relevance",
                 "postClickQualityScore": "landing page experience"}
        weak = [(t, [comps[k] for k in comps if info.get(k) == "BELOW_AVERAGE"]) for _, _, info, t in top]
        weak = [(t, w) for t, w in weak if w]
        share = len(weak) / len(top)
        tally = {}
        for _, w in weak:
            for x in w:
                tally[x] = tally.get(x, 0) + 1
        st = "PASS" if not weak else "WARN" if share <= 0.2 else "FAIL"
        self.add(10, "10.3", "Quality Score parts on top keywords", st,
                 f"{len(weak)} of the top {len(top)} keywords by spend have a below-average part"
                 f"{' (' + ', '.join(f'{k}: {v}' for k, v in sorted(tally.items(), key=lambda x: -x[1])) + ')' if tally else ''}.",
                 "Below-average click rate: sharper headlines. Ad relevance: tighter ad groups. Landing page: faster, matching page.")

    def c11_search_terms(self):
        if not self.has("search_terms"):
            return self.unmeasured(11, "11.1", "Spend on searches that never convert", ["search_terms"])
        terms = {}
        for r in self.d["search_terms"]:
            t = g(r, "searchTermView", "searchTerm", default="")
            x = terms.setdefault(t, {"term": t, "cost": 0.0, "conv": 0.0, "clicks": 0.0, "status": g(r, "searchTermView", "status"),
                                     "campaigns": set()})
            x["cost"] += micros(g(r, "metrics", "costMicros"))
            x["conv"] += num(g(r, "metrics", "conversions"))
            x["clicks"] += num(g(r, "metrics", "clicks"))
            x["campaigns"].add(g(r, "campaign", "name", default=""))
        total = sum(x["cost"] for x in terms.values())
        self.terms_capped = len(self.d["search_terms"]) >= 10000
        if not total:
            return self.add(11, "11.1", "Spend on searches that never convert", "NA", "No search-term spend in the period.")
        bar = max(10.0, 0.5 * (self.target_cpa or self.cpa or 0))
        zero = sorted([x for x in terms.values() if x["conv"] == 0 and x["cost"] >= bar], key=lambda x: -x["cost"])
        zc = sum(x["cost"] for x in zero)
        share = zc / total
        st = "PASS" if share < 0.05 else "WARN" if share <= 0.15 else "FAIL"
        self.zero_terms = [{"term": x["term"], "cost": round(x["cost"], 2), "clicks": int(x["clicks"]),
                            "campaigns": sorted(x["campaigns"]), "status": x["status"]} for x in zero[:40]]
        tail = sum(x["cost"] for x in terms.values() if x["conv"] == 0)
        self.add(11, "11.1", "Spend on searches that never convert", st,
                 f"{share:.0%} of search-term spend ({self.money(zc)} in {self.days} days) went to {len(zero)} searches "
                 f"that each cost {self.money(bar)}+ with no conversion" +
                 (". Top: " + ", ".join(f"'{x['term']}' {self.money(x['cost'])}" for x in zero[:8]) if zero else "") +
                 f". All non-converting searches together, including cheap ones: {self.money(tail)} ({tail / total:.0%})." +
                 (" Only the top 10,000 search terms by cost were read." if self.terms_capped else ""),
                 "Review the list: add clearly irrelevant ones as negatives (exact for one-offs, phrase for patterns). "
                 "Some may be relevant and just need time or a better page.", self.monthly(zc))
        conv_terms = [x for x in terms.values() if x["conv"] > 0]
        term_conv = sum(x["conv"] for x in terms.values())
        if conv_terms and term_conv < 30:
            self.add(11, "11.2", "Balance of waste vs reach (Lin-Rodnitzky ratio)", "NA",
                     f"Only {term_conv:.0f} conversions from search terms in the period; too few to judge the ratio.")
        elif conv_terms and self.conv:
            all_cpa = total / sum(x["conv"] for x in terms.values())
            cv_cpa = sum(x["cost"] for x in conv_terms) / sum(x["conv"] for x in conv_terms)
            lr = all_cpa / cv_cpa if cv_cpa else 0
            st = "PASS" if 1.5 <= lr <= 2.0 else "WARN" if lr < 1.5 or lr <= 3.0 else "FAIL"
            self.add(11, "11.2", "Balance of waste vs reach (Lin-Rodnitzky ratio)", st,
                     f"{lr:.2f} (all-search CPA {self.money(all_cpa)} / converting-search CPA {self.money(cv_cpa)}). "
                     "1.5-2.0 is healthy; above 3 is leaky; below 1.5 may be too restricted.",
                     "Above 2: more negative-keyword work. Below 1.5: test more phrase/broad reach.")
        if self.search and self.has("keywords_all", "campaign_criteria"):
            neg_camp = {g(r, "campaign", "id") for r in self.d["campaign_criteria"]
                        if g(r, "campaignCriterion", "type") == "KEYWORD" and g(r, "campaignCriterion", "negative")}
            neg_camp |= {g(r, "campaign", "id") for r in self.d["keywords_all"] if g(r, "adGroupCriterion", "negative")}
            neg_camp |= {g(r, "campaign", "id") for r in self.d.get("campaign_shared_sets", [])
                         if g(r, "sharedSet", "type") == "NEGATIVE_KEYWORDS"}
            n = sum(1 for c in self.search if c["id"] in neg_camp)
            st = "PASS" if n == len(self.search) else "WARN" if n else "FAIL"
            self.add(11, "11.3", "Every Search campaign has negatives", st,
                     f"{n} of {len(self.search)} enabled Search campaigns have negative keywords.",
                     "Every Search campaign needs negatives from its own search terms plus the shared list.")

    def c12_ads(self):
        if not self.has("ads"):
            return self.unmeasured(12, "12.1", "Ad strength", ["ads"])
        live = [r for r in self.d["ads"] if g(r, "adGroupAd", "status") == "ENABLED"
                and g(r, "campaign", "status", default="ENABLED") == "ENABLED" and g(r, "adGroup", "status", default="ENABLED") == "ENABLED"]
        search_ids = {c["id"] for c in self.search}
        rsas = [r for r in live if g(r, "adGroupAd", "ad", "type") == "RESPONSIVE_SEARCH_AD"]
        rated = [r for r in rsas if g(r, "adGroupAd", "adStrength") in ("POOR", "AVERAGE", "GOOD", "EXCELLENT")]
        if rated:
            good = [r for r in rated if g(r, "adGroupAd", "adStrength") in ("GOOD", "EXCELLENT")]
            share = len(good) / len(rated)
            st = "PASS" if share >= 0.8 else "WARN" if share >= 0.6 else "FAIL"
            self.add(12, "12.1", "Ad strength Good or Excellent", st,
                     f"{len(good)} of {len(rated)} live responsive search ads rated Good/Excellent.",
                     "Add headlines (10-15, different angles), all 4 descriptions, and pin only what must be pinned.")
        else:
            self.add(12, "12.1", "Ad strength Good or Excellent", "NA", "No rated responsive search ads live.")
        if self.has("keywords_all") and self.search:
            groups = {g(r, "adGroup", "id"): g(r, "adGroup", "name") for r in self.d["keywords_all"]
                      if g(r, "campaign", "id") in search_ids and g(r, "adGroup", "status") == "ENABLED"
                      and not g(r, "adGroupCriterion", "negative") and g(r, "adGroupCriterion", "status") == "ENABLED"}
            n_ads = {}
            for r in rsas:
                n_ads[g(r, "adGroup", "id")] = n_ads.get(g(r, "adGroup", "id"), 0) + 1
            none = [groups[x] for x in groups if not n_ads.get(x)]
            two = sum(1 for x in groups if n_ads.get(x, 0) >= 2)
            st = "FAIL" if none else "PASS" if groups and two / len(groups) >= 0.7 else "WARN"
            self.add(12, "12.2", "Every ad group has ads to test", st,
                     f"{len(none)} ad groups with keywords but no live responsive search ad"
                     f"{': ' + ', '.join(none[:5]) if none else ''}. {two} of {len(groups)} have 2+ ads.",
                     "Every ad group: 2-3 responsive search ads with different angles.")
        heads = [len(g(r, "adGroupAd", "ad", "responsiveSearchAd", "headlines", default=[])) for r in rsas]
        descs = [len(g(r, "adGroupAd", "ad", "responsiveSearchAd", "descriptions", default=[])) for r in rsas]
        if heads:
            mh, md = statistics.median(heads), statistics.median(descs)
            under8 = sum(1 for h in heads if h < 8) / len(heads)
            st = "PASS" if mh >= 10 and md >= 3 and under8 < 0.2 else "FAIL" if mh < 7 or md < 3 or under8 >= 0.5 else "WARN"
            self.add(12, "12.3", "Ads use enough headlines and descriptions", st,
                     f"Median ad has {mh:g} headlines and {md:g} descriptions; {under8:.0%} of ads have fewer than 8 headlines.",
                     "Aim for 10-15 headlines and 4 descriptions per ad.")
            sets = [{x.get("text", "").strip().lower() for x in
                     g(r, "adGroupAd", "ad", "responsiveSearchAd", "headlines", default=[])} for r in rsas]
            groups = {}
            for r, hs in zip(rsas, sets):
                groups.setdefault(g(r, "adGroup", "id"), set()).update(hs)
            count = {}
            for hs in groups.values():
                for h in hs:
                    count[h] = count.get(h, 0) + 1
            if len(rsas) >= 5 and len(groups) >= 3:
                common = {h for h, n in count.items() if n / len(groups) >= 0.4}
                share = statistics.median(len(hs & common) / len(hs) for hs in sets if hs)
                st = "PASS" if share <= 0.2 else "WARN" if share <= 0.4 else "FAIL"
                self.add(12, "12.4", "Ad copy is specific to each ad group", st,
                         f"{len(common)} headlines appear in 40%+ of ad groups ({', '.join(repr(h) for h in sorted(common)[:5])}); "
                         f"in the median ad they are {share:.0%} of its headlines." if common else
                         "No headline repeats across most ads.",
                         "Keep shared brand lines to 2-3 slots; the rest should speak to each ad group's own keyword and promise.")
        legacy = [r for r in live if g(r, "adGroupAd", "ad", "type") in ("EXPANDED_TEXT_AD", "TEXT_AD")]
        bad = [r for r in live if g(r, "adGroupAd", "policySummary", "approvalStatus") == "DISAPPROVED"]
        limited = [r for r in live if g(r, "adGroupAd", "policySummary", "approvalStatus") == "APPROVED_LIMITED"]
        st = "FAIL" if bad or len(legacy) > 5 else "WARN" if legacy or limited else "PASS"
        self.add(12, "12.5", "No disapproved or retired ads", st,
                 f"{len(bad)} disapproved, {len(limited)} approved (limited), {len(legacy)} old-format text ads still live.",
                 "Fix disapproved ads (Policy manager); replace old text ads with responsive search ads.")

    def c13_assets(self):
        if not self.search:
            return self.add(13, "13.1", "Sitelinks on every Search campaign", "NA", "No enabled Search campaigns.")
        if not self.has("campaign_assets", "customer_assets"):
            return self.unmeasured(13, "13.1", "Sitelinks on every Search campaign", ["campaign_assets", "customer_assets"])
        camp, acct = {}, {}
        for r in self.d["campaign_assets"]:
            k = (g(r, "campaign", "id"), g(r, "campaignAsset", "fieldType"))
            camp[k] = camp.get(k, 0) + 1
        for r in self.d["customer_assets"]:
            k = g(r, "customerAsset", "fieldType")
            acct[k] = acct.get(k, 0) + 1

        def eff(cid, field):
            return camp.get((cid, field)) or acct.get(field, 0)

        def coverage(sid, name, field, need, fix):
            ok = [c for c in self.search if eff(c["id"], field) >= need]
            share = len(ok) / len(self.search)
            st = "PASS" if share == 1 else "WARN" if share >= 0.5 else "FAIL"
            self.add(13, sid, name, st, f"{len(ok)} of {len(self.search)} Search campaigns have {need}+ ({field.lower()}).", fix)

        coverage("13.1", "Sitelinks on every Search campaign", "SITELINK", 4, "Add at least 4 sitelinks (account level works).")
        ok = [c for c in self.search if eff(c["id"], "CALLOUT") >= 4 and eff(c["id"], "STRUCTURED_SNIPPET") >= 1]
        share = len(ok) / len(self.search)
        self.add(13, "13.2", "Callouts and structured snippets", "PASS" if share == 1 else "WARN" if share >= 0.5 else "FAIL",
                 f"{len(ok)} of {len(self.search)} Search campaigns have 4+ callouts and a structured snippet.",
                 "Add 4+ callouts (what sets you apart) and a structured snippet (services, types).")
        field = "CALL" if self.goal in ("leads", "calls") else "AD_IMAGE"
        has = acct.get(field) or any(camp.get((c["id"], field)) for c in self.search)
        self.add(13, "13.3", "Call asset" if field == "CALL" else "Image assets", "PASS" if has else "WARN",
                 f"{'Found' if has else 'No'} {field.lower().replace('_', ' ')} assets.",
                 "Lead businesses: add a call asset with tracked calls. Stores: add image assets.")

    def c14_landing(self):
        if not self.has("ads"):
            return
        spend = {}
        for r in self.d.get("ad_metrics", []):
            spend[g(r, "adGroupAd", "ad", "id")] = micros(g(r, "metrics", "costMicros"))
        urls = {}
        home_groups = []
        brand_camps = {c["id"] for c in self.camps.values() if "brand" in c["name"].lower() and "non" not in c["name"].lower()}
        for r in self.d["ads"]:
            if not (g(r, "adGroupAd", "status") == "ENABLED" and g(r, "campaign", "status") == "ENABLED"
                    and g(r, "adGroup", "status") == "ENABLED"):
                continue
            for u in g(r, "adGroupAd", "ad", "finalUrls", default=[]) or []:
                urls[u] = urls.get(u, 0) + spend.get(g(r, "adGroupAd", "ad", "id"), 0)
                agname = str(g(r, "adGroup", "name", default="")).lower()
                brandish = g(r, "campaign", "id") in brand_camps or "brand" in agname or self.is_brand(agname)
                if urllib.parse.urlparse(u).path in ("", "/") and not brandish \
                        and g(r, "adGroupAd", "ad", "type") == "RESPONSIVE_SEARCH_AD":
                    home_groups.append(g(r, "adGroup", "name"))
        self.top_urls = [u for u, _ in sorted(urls.items(), key=lambda x: -x[1])[:10]]
        hg = sorted(set(home_groups))
        self.add(14, "14.1", "Ads land on matching pages, not the homepage", "WARN" if hg else "PASS",
                 f"{len(hg)} non-brand ad groups send clicks to the homepage: {', '.join(hg[:6])}." if hg else
                 "Non-brand ads land on specific pages.",
                 "Send each ad group to the page that answers that search (service or product page), with the same promise as the ad.")
        self.url_checks = []

    def check_urls(self, insecure=False):
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        bad, slow = [], []
        for u in getattr(self, "top_urls", []):
            t0 = time.time()
            res = {"url": u}
            try:
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    body = resp.read(400_000).decode("utf-8", "replace")
                    res.update(status=resp.status, final=resp.geturl(), seconds=round(time.time() - t0, 2))
                    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
                    h = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.I | re.S)
                    res["title"] = re.sub(r"\s+|<[^>]+>", " ", m.group(1)).strip()[:120] if m else ""
                    res["h1"] = re.sub(r"\s+|<[^>]+>", " ", h.group(1)).strip()[:120] if h else ""
            except urllib.error.HTTPError as e:
                res.update(status=e.code, final=u, seconds=round(time.time() - t0, 2))
            except Exception as e:  # noqa: BLE001 - report any fetch failure as-is
                res.update(status=0, error=str(e)[:120], seconds=round(time.time() - t0, 2))
            if res.get("status") != 200 or urllib.parse.urlparse(res.get("final", u)).netloc != urllib.parse.urlparse(u).netloc:
                bad.append(res)
            elif res["seconds"] > 4:
                slow.append(res)
            self.url_checks.append(res)
        if not self.url_checks:
            return
        st = "FAIL" if bad else "WARN" if slow else "PASS"
        self.add(14, "14.2", "Landing pages load", st,
                 f"Checked {len(self.url_checks)} top landing pages: {len(bad)} broken or redirected off-site, "
                 f"{len(slow)} slower than 4 seconds for the full HTML." +
                 (" Problems: " + ", ".join(f"{b['url']} ({b.get('status') or b.get('error')})" for b in bad[:5]) if bad else ""),
                 "Fix broken pages first; paid clicks to a dead page are pure loss.")

    # scoring
    def score(self):
        cats = {}
        for s in self.signals:
            if s["status"] in POINTS:
                cats.setdefault(s["category"], []).append(POINTS[s["status"]])
        per = {k: sum(v) / len(v) * 100 for k, v in cats.items()}
        wsum = sum(CATEGORIES[k][1] for k in per)
        overall = sum(per[k] * CATEGORIES[k][1] for k in per) / wsum if wsum else None
        return per, overall

    def result(self):
        per, overall = self.score()
        grade = None if overall is None else "A" if overall >= 90 else "B" if overall >= 80 else "C"
        mat, first = self.maturity() if "history" in self.d else ("unknown", None)
        impact = [s for s in self.signals if s["monthly_impact"]]
        return {
            "account": {"customer_id": self.manifest.get("customer_id"), "name": self.manifest.get("name"),
                        "currency": self.cur, "period": f"{self.manifest.get('start')} to {self.manifest.get('end')}",
                        "days": self.days, "goal": self.goal, "maturity": mat, "first_spend_month": first,
                        "spend": round(self.spend, 2), "conversions": round(self.conv, 1), "value": round(self.value, 2),
                        "cpa": round(self.cpa, 2) if self.cpa else None,
                        "roas": round(self.value / self.spend, 2) if self.spend and self.value else None},
            "score": None if overall is None else round(overall), "grade": grade,
            "categories": {CATEGORIES[k][0]: round(v) for k, v in sorted(per.items())},
            "not_scored": [CATEGORIES[k][0] for k in CATEGORIES if k not in per],
            "signals": self.signals,
            "zero_conversion_search_terms": getattr(self, "zero_terms", []),
            "zero_conversion_spend_monthly": round(sum(s["monthly_impact"] for s in impact if s["id"] == "11.1"), 2),
            "top_landing_pages": getattr(self, "top_urls", []),
            "url_checks": getattr(self, "url_checks", []),
            "ask_owner": self.asks,
            "failed_data": self.failures,
        }


def compare_blueprint(audit, bp):
    """Where the live account differs from the plan. Facts only."""
    planned = {}
    for c in bp.get("campaigns", []):
        for grp in c.get("ad_groups", []):
            for k in grp.get("keywords", []):
                t, m = parse_kw(k)
                planned[(t.lower(), m)] = f"{c.get('name')} > {grp.get('name')}"
    live = {}
    for r in audit.d.get("keywords_all", []):
        if g(r, "adGroupCriterion", "negative") or g(r, "adGroupCriterion", "status") != "ENABLED":
            continue
        live[(g(r, "adGroupCriterion", "keyword", "text", default="").lower(), g(r, "adGroupCriterion", "keyword", "matchType"))] = \
            f"{g(r, 'campaign', 'name')} > {g(r, 'adGroup', 'name')}"
    missing = [f"{kw_notation(t, m)} ({w})" for (t, m), w in planned.items() if (t, m) not in live]
    extra = [f"{kw_notation(t, m)} ({w})" for (t, m), w in live.items() if (t, m) not in planned]
    out = {"planned_keywords": len(planned), "live_keywords": len(live),
           "planned_missing": missing[:50], "live_not_in_plan": extra[:50], "settings": []}
    by_name = {c["name"].lower(): c for c in audit.camps.values()}
    for c in bp.get("campaigns", []):
        lc = by_name.get(str(c.get("name", "")).lower())
        if not lc:
            out["settings"].append(f"Planned campaign '{c.get('name')}' not found by name.")
            continue
        if c.get("bidding") and c["bidding"].upper() != lc["bidding"]:
            out["settings"].append(f"{lc['name']}: bidding {lc['bidding']}, plan {c['bidding']}")
        nets = c.get("networks") or {}
        if bool(nets.get("display")) != lc["display"]:
            out["settings"].append(f"{lc['name']}: Display Network {'on' if lc['display'] else 'off'}, plan {'on' if nets.get('display') else 'off'}")
        if bool(nets.get("search_partners")) != lc["partners"]:
            out["settings"].append(f"{lc['name']}: Search Partners {'on' if lc['partners'] else 'off'}, plan {'on' if nets.get('search_partners') else 'off'}")
        if c.get("budget_daily") and abs(num(c["budget_daily"]) - lc["budget"]) > 0.01:
            out["settings"].append(f"{lc['name']}: budget {lc['budget']:.2f}/day, plan {num(c['budget_daily']):.2f}/day")
    return out


def cmd_audit(a):
    folder = Path(a.data_dir)
    if not folder.is_dir():
        die(f"No data folder at {folder}. Run `gads.py fetch` first.")
    answers = read_json(a.answers) if a.answers else {}
    brand = list(a.brand or []) + list(answers.get("brand_terms", []) if isinstance(answers.get("brand_terms"), list) else
                                       [answers["brand_terms"]] if answers.get("brand_terms") else [])
    bp = read_json(a.blueprint) if a.blueprint else None
    if bp:
        brand += bp.get("brand_terms", [])
    au = Audit(folder, a.goal or (bp or {}).get("goal"), a.target_cpa or num((bp or {}).get("economics", {}).get("target_cpa"), None),
               a.target_roas, brand, answers).run()
    if a.check_urls:
        au.check_urls(a.insecure)
    res = au.result()
    if bp:
        res["blueprint"] = compare_blueprint(au, bp)
    if a.out:
        write_json(a.out, res)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return
    ac = res["account"]
    print(f"{ac['name']} ({fmt_id(ac['customer_id'] or '')}), {ac['period']}")
    print(f"Goal {ac['goal']}, maturity {ac['maturity']}. Spend {ac['spend']:,.2f} {ac['currency']}, "
          f"{ac['conversions']:,.1f} conversions" + (f", CPA {ac['cpa']:,.2f}" if ac["cpa"] else "") +
          (f", ROAS {ac['roas']:.2f}" if ac["roas"] else "") + ".")
    print(f"Score {res['score']}/100 ({res['grade']})" if res["score"] is not None else "Score: not enough data")
    for name, v in res["categories"].items():
        print(f"  {v:>3}  {name}")
    if res["not_scored"]:
        print(f"  not scored: {', '.join(res['not_scored'])}")
    order = {"FAIL": 0, "WARN": 1, "ASK": 2, "UNKNOWN": 3, "PASS": 4, "INFO": 5, "NA": 6}
    print()
    for s in sorted(res["signals"], key=lambda s: (order[s["status"]], s["category"])):
        imp = f" [~{s['monthly_impact']:,.0f}/mo]" if s["monthly_impact"] else ""
        print(f"{s['status']:7} {s['id']:5} {s['name']}{imp}: {s['evidence']}")
    if res["ask_owner"]:
        print("\nAsk the owner (then re-run with --answers):")
        for q in res["ask_owner"]:
            print(f"  {q['key']}: {q['question']}")
    if res["failed_data"]:
        print(f"\nData that failed to load: {', '.join(res['failed_data'])}")
    if bp:
        b = res["blueprint"]
        print(f"\nAgainst the blueprint: {len(b['planned_missing'])} planned keywords missing, "
              f"{len(b['live_not_in_plan'])} live keywords not in the plan, {len(b['settings'])} setting differences.")
        for s in b["settings"]:
            print(f"  {s}")


# ---------- main ----------

def main(argv=None):
    p = argparse.ArgumentParser(description="Google Ads facts for the owner's own account (read-only).")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--business", help="business name, when BRAND_PATH has {business}")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser

    def sp(name):
        return add(name, parents=[common])

    sp("paths")
    s = sp("accounts")
    s.add_argument("--manager", help="a manager (MCC) customer id to list the accounts under")
    s = sp("use")
    s.add_argument("customer_id")
    s.add_argument("--login", help="manager (MCC) customer id, for accounts reached through a manager")
    s = sp("geo")
    s.add_argument("name")
    s.add_argument("--country", help="two-letter country code, e.g. US")

    s = sp("keywords")
    s.add_argument("mode", choices=["ideas", "volume"])
    s.add_argument("keyword", nargs="*", help="keywords to check (volume mode)")
    s.add_argument("--seed", action="append", default=[], help="seed keyword (ideas mode); repeat")
    s.add_argument("--url", help="a page to pull ideas from (ideas mode)")
    s.add_argument("--file", help="text file, one keyword per line (volume mode)")
    s.add_argument("--geo", action="append", required=True, help="location ID from `gads.py geo`; repeat")
    s.add_argument("--lang", default="1000", help="language ID (1000 = English, 1003 = Spanish, 1002 = French)")
    s.add_argument("--limit", type=int, default=80)
    s.add_argument("--customer")
    s.add_argument("--login")

    s = sp("budget")
    s.add_argument("--daily", type=float)
    s.add_argument("--monthly", type=float)
    s.add_argument("--cpc", type=float, required=True, help="expected cost per click")
    s.add_argument("--cvr", type=float, help="expected conversion rate, e.g. 0.05")
    s.add_argument("--lead-value", type=float, help="average value of a sale that comes from a lead")
    s.add_argument("--close-rate", type=float, help="share of leads that become sales, e.g. 0.25")
    s.add_argument("--json", action="store_true")

    s = sp("blueprint")
    s.add_argument("action", choices=["check", "render"])
    s.add_argument("file")
    s.add_argument("--out")

    s = sp("fetch")
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--customer")
    s.add_argument("--login")

    s = sp("audit")
    s.add_argument("data_dir")
    s.add_argument("--goal", choices=["leads", "sales", "calls", "awareness"])
    s.add_argument("--target-cpa", type=float)
    s.add_argument("--target-roas", type=float)
    s.add_argument("--brand", action="append", help="brand term; repeat for misspellings")
    s.add_argument("--answers", help="JSON file with the owner's answers to the ask_owner questions")
    s.add_argument("--blueprint", help="blueprint JSON to compare the live account against")
    s.add_argument("--check-urls", action="store_true", help="fetch the top landing pages")
    s.add_argument("--insecure", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--out", help="write the full result JSON here")

    a = p.parse_args(argv)
    if a.cmd == "budget" and not (a.daily or a.monthly):
        die("Give --daily or --monthly.")
    {"paths": cmd_paths, "accounts": cmd_accounts, "use": cmd_use, "geo": cmd_geo, "keywords": cmd_keywords,
     "budget": cmd_budget, "blueprint": cmd_blueprint, "fetch": cmd_fetch, "audit": cmd_audit}[a.cmd](a)


if __name__ == "__main__":
    main()
