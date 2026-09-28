#!/usr/bin/env python3
"""SEO checks for the owner's own site and drafts. Stdlib only; macOS, Linux, Windows.

Deterministic facts only. Judgement (what to fix first, how to rewrite) is the agent's job.

  seo.py paths [--business NAME]            # where reports/drafts go + which brand files exist
  seo.py page URL [--json]                  # one page: status, title, meta, headings, schema,
                                            #   images, links, local signals, flags
  seo.py site URL [--max-pages 25] [--json] # robots.txt (incl. AI crawlers), sitemap, llms.txt,
                                            #   http->https, crawl of up to N pages, broken links
  seo.py speed URL [--strategy mobile|desktop] [--json]
                                            # Core Web Vitals via Google PageSpeed Insights
                                            #   (free; optional own key in PAGESPEED_API_KEY)
  seo.py text FILE [--keyword "K"] [--type blog|service|location|home|product] [--json]
                                            # grade a draft (.md or .html) before it goes to the owner

  seo.py nap URL [URL...] --name N --address A --phone P
                                            # name/address/phone on the site vs the owner's Google listing
  seo.py gbp answers.json [--industry professional]
                                            # Google Business Profile completeness score (0/1/2 per field)
  seo.py decay current.csv previous.csv [--metric clicks]
                                            # pages losing traffic, from two Search Console Pages exports

Common flags: --insecure (skip TLS verification when this Python has no CA bundle; says so).
Exit codes: 0 ok, 1 fetch failed / gate failed, 2 config or usage problem.
"""
import argparse
import datetime as dt
import html as htmllib
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
UA = "Mozilla/5.0 (compatible; bbm-seo-check/1.0; +https://github.com/Brand-Building-Machine/bbm-buzz-agents)"
TIMEOUT = 20
MAX_BYTES = 5_000_000

# Thresholds. Sources: claude-seo (AgriciDaniel, MIT) quality gates; Google docs where noted.
TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 120, 160
MIN_WORDS = {"home": 500, "service": 800, "location": 500, "blog": 1500, "product": 300, "page": 300}
KEYWORD_DENSITY_MAX = 3.0       # % of words; above this reads as stuffing
PASSAGE_MIN, PASSAGE_MAX = 130, 170   # self-contained answer block, heuristic not a Google rule
SLOW_SECONDS = 2.0

# AI crawlers: (token, owner, what blocking it does). Search bots decide citations; training
# bots only decide model training. Blocking a training bot does NOT hide you from AI search.
AI_BOTS = [
    ("OAI-SearchBot", "OpenAI", "search"),
    ("ChatGPT-User", "OpenAI", "user"),
    ("GPTBot", "OpenAI", "training"),
    ("Claude-SearchBot", "Anthropic", "search"),
    ("Claude-User", "Anthropic", "user"),
    ("ClaudeBot", "Anthropic", "training"),
    ("PerplexityBot", "Perplexity", "search"),
    ("Perplexity-User", "Perplexity", "user"),
    ("Google-Extended", "Google", "training"),
    ("Applebot-Extended", "Apple", "training"),
    ("CCBot", "Common Crawl", "training"),
    ("Bytespider", "ByteDance", "training"),
    ("meta-externalagent", "Meta", "training"),
]
SEARCH_BOTS = ["Googlebot", "Bingbot"]

LOCAL_TYPES = {
    "LocalBusiness", "ProfessionalService", "LegalService", "Attorney", "AccountingService",
    "FinancialService", "InsuranceAgency", "RealEstateAgent", "HomeAndConstructionBusiness",
    "Plumber", "Electrician", "HVACBusiness", "RoofingContractor", "GeneralContractor",
    "HousePainter", "Locksmith", "MovingCompany", "AutomotiveBusiness", "AutoRepair",
    "HealthAndBeautyBusiness", "BeautySalon", "DaySpa", "HairSalon", "MedicalBusiness",
    "Dentist", "Physician", "MedicalClinic", "Optician", "Pharmacy", "FoodEstablishment",
    "Restaurant", "CafeOrCoffeeShop", "Bakery", "Store", "SportsActivityLocation",
    "ExerciseGym", "LodgingBusiness", "Hotel", "ChildCare", "EmploymentAgency",
    "EntertainmentBusiness", "TravelAgency", "Veterinarian", "CleaningService",
}
# Types that still validate but no longer earn rich results for most sites.
LIMITED_TYPES = {
    "FAQPage": "FAQ rich results are limited to well-known government and health sites (Google, Aug 2023). Fine to keep; expect no FAQ snippet.",
    "HowTo": "HowTo rich results were removed (Google, Sep 2023). Fine to keep; expect no rich result.",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------- config ----------

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


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


def cmd_paths(a):
    cfg = load_config()
    if not cfg.get("PROPOSED_PATH"):
        die("Config has no PROPOSED_PATH. Run workspace-config.")
    out = Path(cfg["PROPOSED_PATH"]).expanduser() / "seo"
    if a.business:
        out = out / a.business
    print(f"reports and drafts: {out}")
    pattern = cfg.get("BRAND_PATH") or ""
    if not pattern:
        print("brand folder: NOT SET (run workspace-config, then brand-bible)")
        return
    if "{business}" in pattern and not a.business:
        root = Path(pattern.split("{business}")[0]).expanduser()
        names = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []
        print(f"brand folders are per business ({pattern}). Pass --business. Found: {', '.join(names) or 'none'}")
        return
    bd = brand_dir(cfg, a.business)
    print(f"brand folder: {bd}")
    for f in ["brand-bible.md", "voice-agent.md", "offers.md", "root.css"]:
        print(f"  {f}: {'yes' if (bd / f).exists() else 'MISSING'}")


# ---------- fetching ----------

class Fetch:
    def __init__(self, url, status, final_url, headers, body, seconds, error=None, hops=0):
        self.url, self.status, self.final_url = url, status, final_url
        self.headers, self.body, self.seconds, self.error, self.hops = headers, body, seconds, error, hops

    @property
    def text(self):
        ctype = self.headers.get("content-type", "")
        m = re.search(r"charset=([\w-]+)", ctype, re.I)
        enc = m.group(1) if m else "utf-8"
        try:
            return self.body.decode(enc, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


class _Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.hops = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


INSECURE = False


def safe_url(url):
    """Percent-encode spaces and other characters a sloppy href can carry (http.client rejects them)."""
    return urllib.parse.quote(url.strip(), safe=":/?#[]@!$&'()*+,;=%~")


def fetch(url, method="GET"):
    url = safe_url(url)
    ctx = ssl._create_unverified_context() if INSECURE else ssl.create_default_context()
    red = _Redirects()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), red)
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en"})
    t0 = time.time()
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES) if method == "GET" else b""
            return Fetch(url, r.status, r.geturl(), {k.lower(): v for k, v in r.headers.items()},
                         body, time.time() - t0, hops=red.hops)
    except urllib.error.HTTPError as e:
        body = e.read(MAX_BYTES) if hasattr(e, "read") else b""
        return Fetch(url, e.code, e.geturl() or url, {k.lower(): v for k, v in (e.headers or {}).items()},
                     body, time.time() - t0, hops=red.hops)
    except ssl.SSLCertVerificationError as e:
        return Fetch(url, 0, url, {}, b"", time.time() - t0,
                     error=f"TLS certificate not verified ({e.reason}). If the site opens fine in a browser, "
                           "this Python lacks CA certificates: re-run with --insecure.")
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return Fetch(url, 0, url, {}, b"", time.time() - t0,
                         error="TLS certificate not verified. If the site opens fine in a browser, "
                               "this Python lacks CA certificates: re-run with --insecure.")
        return Fetch(url, 0, url, {}, b"", time.time() - t0, error=str(reason))


def normalize_url(url):
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


# ---------- HTML parsing ----------

SKIP_TEXT = {"script", "style", "noscript", "template", "svg", "head"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.in_title = "", False
        self.meta, self.links_rel, self.hreflang = {}, {}, []
        self.lang = ""
        self.headings, self._h = [], None
        self.images, self.anchors, self.iframes = [], [], []
        self.jsonld, self._ld = [], None
        self.scripts, self.blocking_scripts, self.in_head = 0, 0, False
        self.text_parts, self._skip = [], 0
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        elif tag == "title" and not self.title:
            self.in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if key and key not in self.meta:
                self.meta[key] = a.get("content", "")
            if "charset" in a:
                self.meta.setdefault("charset", a["charset"])
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "alternate" and a.get("hreflang"):
                self.hreflang.append((a["hreflang"], a.get("href", "")))
            elif rel:
                for r in rel.split():
                    self.links_rel.setdefault(r, a.get("href", ""))
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._h = [int(tag[1]), []]
        elif tag == "img":
            self.images.append(a)
        elif tag == "a":
            self._a = [a.get("href", ""), a.get("rel", ""), []]
        elif tag == "iframe":
            self.iframes.append(a.get("src", ""))
        elif tag == "script":
            self.scripts += 1
            if (self.in_head and a.get("src") and "async" not in a and "defer" not in a
                    and a.get("type", "").lower() != "module"):
                self.blocking_scripts += 1
            if "ld+json" in a.get("type", "").lower():
                self._ld = []
        if tag in SKIP_TEXT and tag not in VOID:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "head":
            self.in_head = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._h:
            self.headings.append((self._h[0], " ".join("".join(self._h[1]).split())))
            self._h = None
        elif tag == "a" and self._a:
            self.anchors.append((self._a[0], self._a[1], " ".join("".join(self._a[2]).split())))
            self._a = None
        elif tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None
        if tag in SKIP_TEXT and self._skip:
            self._skip -= 1
        if tag in ("p", "div", "li", "br", "section", "article", "td", "tr") and not self._skip:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self.in_title:
            self.title += data
        if self._skip:
            return
        if self._h:
            self._h[1].append(data)
        if self._a:
            self._a[2].append(data)
        self.text_parts.append(data)


def words(text):
    return re.findall(r"[A-Za-z0-9À-ɏ'’]+", text)


def schema_types(blocks):
    """(types, errors, nodes) from JSON-LD strings; walks @graph and nested objects."""
    types, errors, nodes = [], [], []

    def walk(o):
        if isinstance(o, dict):
            t = o.get("@type")
            if t:
                for x in (t if isinstance(t, list) else [t]):
                    types.append(str(x))
                nodes.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for i, raw in enumerate(blocks):
        try:
            data = json.loads(raw.strip())
        except ValueError as e:
            errors.append(f"JSON-LD block {i + 1} is not valid JSON: {e}")
            continue
        tops = data if isinstance(data, list) else [data]
        if any(isinstance(t, dict) and "@context" not in t for t in tops):
            errors.append(f"JSON-LD block {i + 1} has no @context (should be https://schema.org).")
        ph = SCHEMA_PLACEHOLDER_RE.findall(raw)
        if ph:
            errors.append(f"JSON-LD block {i + 1} contains placeholder text: {', '.join(sorted(set(ph))[:5])}")
        walk(data)
    return types, errors, nodes


SCHEMA_PLACEHOLDER_RE = re.compile(r"\[(?:Business Name|Your [^\]]{1,30}|[A-Z][A-Z _]{3,30})\]|\bREPLACE(?:_[A-Z]+)*\b|\{\{[^}]+\}\}|\bXXX+\b")
SHELL_RE = re.compile(r'<div[^>]+id=["\'](?:root|app|__next|__nuxt)["\'][^>]*>\s*</div>|enable javascript', re.I)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")


def analyze_html(html_text, url, status=200, headers=None, seconds=None, hops=0):
    headers = headers or {}
    p = PageParser()
    try:
        p.feed(html_text)
        p.close()
    except Exception as e:  # malformed markup should not kill the audit
        p.text_parts.append(f" [parser stopped early: {e}]")
    host = urllib.parse.urlparse(url).netloc.lower()
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.text_parts))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    wc = len(words(text))
    title = " ".join(htmllib.unescape(p.title).split())
    desc = " ".join(p.meta.get("description", "").split())
    robots = (p.meta.get("robots", "") + " " + headers.get("x-robots-tag", "")).lower()
    canonical = p.links_rel.get("canonical", "")
    internal, external, nofollow = [], [], 0
    tel, mailto = [], []
    for href, rel, _txt in p.anchors:
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        if href.lower().startswith("tel:"):
            tel.append(href[4:].strip())
            continue
        if href.lower().startswith("mailto:"):
            mailto.append(href[7:].split("?")[0])
            continue
        absu = urllib.parse.urljoin(url, href).split("#")[0]
        if "nofollow" in rel.lower():
            nofollow += 1
        (internal if urllib.parse.urlparse(absu).netloc.lower() == host else external).append(absu)
    imgs = p.images
    no_alt = [i.get("src", "")[:120] for i in imgs if "alt" not in i]
    empty_alt = sum(1 for i in imgs if "alt" in i and not i["alt"].strip())
    no_dims = sum(1 for i in imgs if not (i.get("width") and i.get("height")))
    lazy = sum(1 for i in imgs if i.get("loading", "").lower() == "lazy")
    types, ld_errors, nodes = schema_types(p.jsonld)
    h1s = [t for lvl, t in p.headings if lvl == 1]
    local_nodes = [n for n in nodes if set((n.get("@type") if isinstance(n.get("@type"), list)
                                            else [n.get("@type")])) & LOCAL_TYPES]
    phones = sorted(set(m.group(0).strip() for m in PHONE_RE.finditer(text)))[:5]
    maps = [s for s in p.iframes if "google.com/maps" in s or "maps.google" in s]
    first_img = imgs[0] if imgs else {}
    mixed = len(re.findall(r"""\ssrc=["']http://""", html_text, re.I)) if url.lower().startswith("https://") else 0
    r = {
        "url": url, "status": status, "seconds": round(seconds, 2) if seconds is not None else None,
        "redirect_hops": hops, "https": url.lower().startswith("https://"),
        "title": title, "title_length": len(title),
        "meta_description": desc, "meta_description_length": len(desc),
        "canonical": canonical, "robots": robots.strip(), "viewport": bool(p.meta.get("viewport")),
        "lang": p.lang, "hreflang": p.hreflang,
        "h1": h1s, "headings": [f"H{lvl} {t}" for lvl, t in p.headings][:60],
        "word_count": wc, "scripts": p.scripts, "render_blocking_scripts": p.blocking_scripts,
        "js_shell": bool(SHELL_RE.search(html_text)), "mixed_content": mixed,
        "hero_image": {"src": first_img.get("src", "")[:120], "lazy": first_img.get("loading", "").lower() == "lazy",
                       "fetchpriority_high": first_img.get("fetchpriority", "").lower() == "high"} if imgs else None,
        "business_site_links": sorted({u for u in internal + external if ".business.site" in u})[:5],
        "images": {"total": len(imgs), "missing_alt": len(no_alt), "missing_alt_src": no_alt[:10],
                   "empty_alt": empty_alt, "missing_dimensions": no_dims, "lazy": lazy},
        "links": {"internal": len(internal), "external": len(external), "nofollow": nofollow,
                  "internal_urls": sorted(set(internal))},
        "schema_types": sorted(set(types)), "schema_errors": ld_errors,
        "open_graph": {k: p.meta.get(k, "") for k in ("og:title", "og:description", "og:image", "og:type")},
        "local": {"schema_local_business": bool(local_nodes),
                  "schema_address": any(isinstance(n.get("address"), (dict, str)) for n in local_nodes),
                  "schema_phone": any(n.get("telephone") for n in local_nodes),
                  "schema_hours": any(n.get("openingHours") or n.get("openingHoursSpecification") for n in local_nodes),
                  "schema_geo": any(n.get("geo") for n in local_nodes),
                  "schema_sameas": any(n.get("sameAs") for n in local_nodes),
                  "tel_links": tel[:5], "phones_in_text": phones, "emails": sorted(set(mailto))[:5],
                  "google_map_embed": bool(maps)},
        "text_sample": text[:600],
    }
    r["flags"] = page_flags(r)
    return r


def flag(sev, code, msg):
    return {"severity": sev, "code": code, "message": msg}


def page_flags(r):
    f = []
    if r["status"] != 200:
        f.append(flag("critical", "status", f"HTTP {r['status']} (search engines need 200)."))
    if "noindex" in r["robots"]:
        f.append(flag("critical", "noindex", "Page tells search engines not to index it (noindex). Intentional?"))
    if not r["https"]:
        f.append(flag("high", "no_https", "Page is not served over HTTPS."))
    if not r["title"]:
        f.append(flag("critical", "title_missing", "No <title>."))
    elif r["title_length"] > TITLE_MAX:
        f.append(flag("medium", "title_long", f"Title is {r['title_length']} chars; Google usually cuts past ~{TITLE_MAX}."))
    elif r["title_length"] < TITLE_MIN:
        f.append(flag("medium", "title_short", f"Title is {r['title_length']} chars; room to add the service and place."))
    if not r["meta_description"]:
        f.append(flag("high", "desc_missing", "No meta description; Google will pick a snippet itself."))
    elif r["meta_description_length"] > DESC_MAX:
        f.append(flag("low", "desc_long", f"Meta description is {r['meta_description_length']} chars; cut past ~{DESC_MAX}."))
    elif r["meta_description_length"] < DESC_MIN:
        f.append(flag("low", "desc_short", f"Meta description is {r['meta_description_length']} chars; aim {DESC_MIN}-{DESC_MAX}."))
    if not r["h1"]:
        f.append(flag("high", "h1_missing", "No H1 heading."))
    elif len(r["h1"]) > 1:
        f.append(flag("low", "h1_multiple", f"{len(r['h1'])} H1 headings; one clear H1 is simpler."))
    if not r["canonical"]:
        f.append(flag("medium", "canonical_missing", "No canonical link."))
    elif r["canonical"].rstrip("/") != r["url"].rstrip("/") and not r["canonical"].startswith("/"):
        f.append(flag("low", "canonical_other", f"Canonical points to another URL: {r['canonical']}"))
    if not r["viewport"]:
        f.append(flag("high", "viewport_missing", "No mobile viewport tag; Google indexes the mobile version."))
    if not r["lang"]:
        f.append(flag("low", "lang_missing", "No lang attribute on <html>."))
    if r["word_count"] < 50 and r.get("js_shell"):
        f.append(flag("critical", "js_shell",
                      f"Only {r['word_count']} words in the raw HTML and the page is a JavaScript app shell. "
                      "Crawlers that don't run JavaScript (most AI crawlers) see an empty page."))
    elif r["word_count"] < 150:
        f.append(flag("high", "js_or_empty",
                      f"Only {r['word_count']} words in the raw HTML. Content may load by JavaScript, which many AI crawlers do not run."))
    elif r["word_count"] < MIN_WORDS["page"]:
        f.append(flag("medium", "thin", f"{r['word_count']} words; likely too thin to rank for anything competitive."))
    im = r["images"]
    if im["missing_alt"]:
        f.append(flag("medium", "img_alt", f"{im['missing_alt']} of {im['total']} images have no alt attribute."))
    if im["missing_dimensions"] and im["total"]:
        f.append(flag("low", "img_dims", f"{im['missing_dimensions']} images lack width/height (layout shift risk)."))
    hero = r.get("hero_image")
    if hero and hero["lazy"]:
        f.append(flag("medium", "hero_lazy", "The first image is lazy-loaded; if it is the main (hero) image this slows the page's largest paint."))
    if r.get("render_blocking_scripts", 0) >= 3:
        f.append(flag("low", "render_blocking", f"{r['render_blocking_scripts']} scripts in <head> load without async/defer (slows first paint)."))
    if r.get("mixed_content"):
        f.append(flag("medium", "mixed_content", f"{r['mixed_content']} resources load over http:// on an https page."))
    if r.get("business_site_links"):
        f.append(flag("medium", "business_site", "Links to a *.business.site page; Google shut those sites down in 2024."))
    if not r["schema_types"]:
        f.append(flag("medium", "schema_missing", "No structured data (JSON-LD)."))
    for e in r["schema_errors"]:
        f.append(flag("high", "schema_invalid", e))  # parse errors, missing @context, placeholders
    for t, note in LIMITED_TYPES.items():
        if t in r["schema_types"]:
            f.append(flag("info", f"schema_{t.lower()}", note))
    if not r["open_graph"].get("og:image"):
        f.append(flag("low", "og_image", "No og:image; shared links show no picture."))
    if r["redirect_hops"] > 1:
        f.append(flag("low", "redirect_chain", f"{r['redirect_hops']} redirects before the page loads."))
    if r["seconds"] and r["seconds"] > SLOW_SECONDS:
        f.append(flag("low", "slow", f"HTML took {r['seconds']}s to download; check `seo.py speed`."))
    if r["links"]["internal"] < 3:
        f.append(flag("low", "few_internal_links", f"{r['links']['internal']} internal links; pages need links in and out."))
    return f


def analyze_url(url):
    f = fetch(url)
    if f.error:
        return {"url": url, "status": 0, "error": f.error, "flags": [flag("critical", "fetch", f.error)]}
    ctype = f.headers.get("content-type", "")
    if "html" not in ctype and f.body[:200].lstrip()[:1] != b"<":
        return {"url": f.final_url, "status": f.status, "error": f"Not HTML ({ctype})",
                "flags": [flag("medium", "not_html", f"Not an HTML page ({ctype}).")]}
    return analyze_html(f.text, f.final_url, f.status, f.headers, f.seconds, f.hops)


# ---------- site-level ----------

def robots_report(robots_text, base):
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_text.splitlines())
    home = base.rstrip("/") + "/"
    bots = []
    for token, owner, kind in AI_BOTS:
        bots.append({"bot": token, "owner": owner, "kind": kind, "allowed": rp.can_fetch(token, home)})
    search = {b: rp.can_fetch(b, home) for b in SEARCH_BOTS}
    everyone = rp.can_fetch("*", home)
    return {"ai_bots": bots, "search_bots": search, "all_bots_home_allowed": everyone,
            "sitemaps": rp.site_maps() or []}


SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap(xml_bytes):
    """(kind, urls, lastmod_count) where kind is 'index' or 'urlset'."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return "invalid", [], 0
    tag = root.tag.split("}")[-1]
    locs = [e.text.strip() for e in root.iter() if e.tag.split("}")[-1] == "loc" and e.text]
    lastmods = sum(1 for e in root.iter() if e.tag.split("}")[-1] == "lastmod")
    return ("index" if tag == "sitemapindex" else "urlset"), locs, lastmods


def llms_report(f):
    if f.error or f.status != 200:
        return {"present": False}
    t = f.text.lstrip()
    ctype = f.headers.get("content-type", "")
    return {"present": not t.lower().startswith("<"), "starts_with_h1": t.startswith("# "),
            "content_type": ctype, "bytes": len(f.body)}


def cmd_site(a):
    base = normalize_url(a.url)
    pu = urllib.parse.urlparse(base)
    origin = f"{pu.scheme}://{pu.netloc}"
    out = {"site": origin, "checked": dt.datetime.now().isoformat(timespec="seconds"), "flags": []}
    home = fetch(origin + "/")
    if home.error:
        die(f"Could not fetch {origin}/: {home.error}", 1)
    final = urllib.parse.urlparse(home.final_url)
    origin = f"{final.scheme}://{final.netloc}"
    out["final_origin"] = origin
    # http -> https
    if final.scheme == "https":
        h = fetch(f"http://{final.netloc}/")
        ok = (not h.error) and h.final_url.startswith("https://")
        out["http_redirects_to_https"] = ok
        if not ok:
            out["flags"].append(flag("high", "http_no_redirect", "http:// version does not redirect to https://."))
    # robots
    rb = fetch(origin + "/robots.txt")
    if rb.status >= 500:
        out["flags"].append(flag("critical", "robots_5xx",
                                 f"robots.txt returns HTTP {rb.status}. Google treats a server error here as 'crawl nothing'."))
    if rb.status == 200 and not rb.error and not rb.body.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        out["robots"] = robots_report(rb.text, origin)
        out["robots_txt"] = rb.text[:3000]
        if not out["robots"]["all_bots_home_allowed"]:
            out["flags"].append(flag("critical", "robots_block_all", "robots.txt blocks the homepage for all crawlers."))
        for b, ok in out["robots"]["search_bots"].items():
            if not ok:
                out["flags"].append(flag("critical", "robots_block_search", f"robots.txt blocks {b}."))
        for b in out["robots"]["ai_bots"]:
            if not b["allowed"] and b["kind"] in ("search", "user"):
                out["flags"].append(flag("high", "robots_block_ai_search",
                                         f"robots.txt blocks {b['bot']} ({b['owner']}), which decides whether you get cited in AI answers."))
    else:
        out["robots"] = None
        out["flags"].append(flag("low", "robots_missing", "No robots.txt (everything allowed; fine, but no sitemap pointer)."))
    # sitemap
    candidates = (out["robots"] or {}).get("sitemaps") or [origin + "/sitemap.xml", origin + "/sitemap_index.xml"]
    sm = {"found": [], "url_count": 0, "lastmod": 0}
    sm_problem = False
    page_urls = []
    for sm_url in candidates[:3]:
        f = fetch(sm_url)
        if f.error or f.status != 200:
            continue
        if f.body.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
            continue  # an HTML page answering at /sitemap.xml is not a sitemap
        if not f.body.strip():
            out["flags"].append(flag("high", "sitemap_empty", f"Sitemap answers but is empty: {sm_url}"))
            sm_problem = True
            continue
        kind, locs, lm = parse_sitemap(f.body)
        if kind == "invalid":
            out["flags"].append(flag("high", "sitemap_invalid", f"Sitemap is not valid XML: {sm_url}"))
            sm_problem = True
            continue
        sm["found"].append(sm_url)
        if kind == "index":
            for child in locs[:5]:
                cf = fetch(child)
                if cf.error or cf.status != 200:
                    continue
                _, clocs, clm = parse_sitemap(cf.body)
                page_urls += clocs
                sm["lastmod"] += clm
        else:
            page_urls += locs
            sm["lastmod"] += lm
        break
    sm["url_count"] = len(page_urls)
    out["sitemap"] = sm
    if not sm["found"] and not sm_problem:
        out["flags"].append(flag("medium", "sitemap_missing", "No XML sitemap found (checked robots.txt, /sitemap.xml, /sitemap_index.xml)."))
    # soft 404: a page that cannot exist should say 404
    probe = fetch(f"{origin}/this-page-should-not-exist-{os.urandom(4).hex()}")
    out["soft_404"] = (not probe.error) and probe.status == 200
    if out["soft_404"]:
        out["flags"].append(flag("medium", "soft_404",
                                 "A made-up URL returns 200 instead of 404, so search engines can index junk pages."))
    # llms.txt
    out["llms_txt"] = llms_report(fetch(origin + "/llms.txt"))
    if not out["llms_txt"]["present"]:
        out["flags"].append(flag("info", "llms_missing",
                                 "No /llms.txt. Optional and unproven: no major AI search engine has said it uses it."))
    # crawl
    host = final.netloc.lower()
    queue = [origin + "/"] + [u for u in page_urls if urllib.parse.urlparse(u).netloc.lower() == host]
    seen, pages, link_targets = set(), [], set()
    while queue and len(pages) < a.max_pages:
        u = queue.pop(0).split("#")[0]
        if u.rstrip("/") in seen:
            continue
        seen.add(u.rstrip("/"))
        r = analyze_url(u)
        pages.append(r)
        for li in r.get("links", {}).get("internal_urls", []):
            if not re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4|css|js)$", li, re.I):
                link_targets.add(li)
                if not page_urls and li.rstrip("/") not in seen:
                    queue.append(li)
        time.sleep(0.2)
    out["pages"] = [{k: v for k, v in p.items() if k not in ("text_sample", "headings")} for p in pages]
    for p in out["pages"]:
        if "links" in p:
            p["links"] = {k: v for k, v in p["links"].items() if k != "internal_urls"}
    # site-wide patterns
    ok = [p for p in pages if p.get("status") == 200 and "title" in p]
    for field, code, label in (("title", "dup_title", "title"), ("meta_description", "dup_desc", "meta description")):
        groups = {}
        for p in ok:
            if p[field]:
                groups.setdefault(p[field], []).append(p["url"])
        for val, urls in groups.items():
            if len(urls) > 1:
                out["flags"].append(flag("medium", code, f"{len(urls)} pages share the same {label}: \"{val[:70]}\""))
    # broken internal links (targets not crawled)
    unchecked = sorted({t.rstrip("/") or t for t in link_targets if t.rstrip("/") not in seen})[:40]
    broken = []
    for t in unchecked:
        f = fetch(t)
        if f.error or f.status >= 400:
            broken.append({"url": t, "status": f.status, "error": f.error})
        time.sleep(0.1)
    broken += [{"url": p["url"], "status": p.get("status"), "error": p.get("error")} for p in pages
               if p.get("status", 0) >= 400 or p.get("status") == 0]
    out["broken_internal_links"] = broken
    out["links_checked"] = len(unchecked) + len(pages)
    for b in broken:
        out["flags"].append(flag("high", "broken_link", f"Broken internal link: {b['url']} ({b['status'] or b['error']})"))
    out["summary"] = {
        "pages_crawled": len(pages),
        "page_flag_counts": count_flags([fl for p in pages for fl in p.get("flags", [])]),
        "site_flag_counts": count_flags(out["flags"]),
    }
    emit(out, a.json, print_site)
    return 0


def count_flags(flags):
    c = {}
    for fl in flags:
        c[fl["severity"]] = c.get(fl["severity"], 0) + 1
    return c


# ---------- speed (PageSpeed Insights) ----------

CWV = {  # metric: (good_max, poor_min, unit)
    "LCP": (2500, 4000, "ms"), "INP": (200, 500, "ms"), "CLS": (0.1, 0.25, ""),
    "FCP": (1800, 3000, "ms"), "TTFB": (800, 1800, "ms"),
}


def rate(metric, value):
    good, poor, _ = CWV[metric]
    return "good" if value <= good else ("poor" if value > poor else "needs improvement")


def parse_psi(data):
    lh = data.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    out = {"performance_score": None, "lab": {}, "field": {}, "field_scope": None, "opportunities": []}
    perf = lh.get("categories", {}).get("performance", {}).get("score")
    if perf is not None:
        out["performance_score"] = round(perf * 100)
    for aid, name in (("largest-contentful-paint", "LCP"), ("cumulative-layout-shift", "CLS"),
                      ("first-contentful-paint", "FCP"), ("total-blocking-time", "TBT"),
                      ("server-response-time", "TTFB")):
        v = audits.get(aid, {}).get("numericValue")
        if v is not None:
            out["lab"][name] = round(v, 3) if name == "CLS" else round(v)
    fmap = {"LARGEST_CONTENTFUL_PAINT_MS": "LCP", "INTERACTION_TO_NEXT_PAINT": "INP",
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": "CLS", "FIRST_CONTENTFUL_PAINT_MS": "FCP",
            "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "TTFB"}
    for src in ("loadingExperience", "originLoadingExperience"):
        m = data.get(src, {}).get("metrics", {})
        if m:
            for k, name in fmap.items():
                if k in m and "percentile" in m[k]:
                    v = m[k]["percentile"]
                    v = v / 100 if name == "CLS" else v
                    out["field"][name] = {"p75": v, "rating": rate(name, v)}
            out["field_scope"] = "this URL" if src == "loadingExperience" else "whole site (origin)"
            break
    for aid, au in audits.items():
        det = au.get("details", {})
        if det.get("type") == "opportunity" and (au.get("score") or 1) < 0.9 and det.get("overallSavingsMs", 0) > 100:
            out["opportunities"].append({"id": aid, "title": au.get("title"), "savings_ms": round(det["overallSavingsMs"])})
    out["opportunities"].sort(key=lambda o: -o["savings_ms"])
    out["opportunities"] = out["opportunities"][:8]
    return out


def cmd_speed(a):
    url = normalize_url(a.url)
    q = {"url": url, "strategy": a.strategy, "category": "performance"}
    key = os.environ.get("PAGESPEED_API_KEY")
    if key:
        q["key"] = key
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(q)
    global TIMEOUT
    TIMEOUT = 90
    f = fetch(api)
    if f.error or f.status != 200:
        msg = f.error or f.text[:300]
        if f.status == 429:
            msg = "PageSpeed Insights rate limit hit. Wait a minute, or set the owner's own free key in PAGESPEED_API_KEY."
        die(f"PageSpeed Insights failed: {msg}", 1)
    out = parse_psi(json.loads(f.text))
    out.update({"url": url, "strategy": a.strategy})
    emit(out, a.json, print_speed)
    return 0


# ---------- draft grading ----------

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def split_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, text[m.end():]


def md_structure(body):
    heads, paras, buf, lists, tables, links = [], [], [], 0, 0, []
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            heads.append((len(m.group(1)), m.group(2).strip()))
            paras.append(None)  # section boundary marker
            continue
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            lists += 1
        if line.strip().startswith("|"):
            tables += 1
        links += re.findall(r"\]\(([^)\s]+)", line)
        if line.strip():
            buf.append(line.strip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return heads, paras, lists, tables, links


def strip_md(s):
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"[*_`>|#]", " ", s)


def html_to_md(raw):
    """Rough HTML -> markdown so drafts in either format get the same checks."""
    s = re.sub(r"(?is)<(script|style|noscript|head)[^>]*>.*?</\1>", " ", raw)
    s = re.sub(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>",
               lambda m: "\n\n" + "#" * int(m.group(1)) + " " + re.sub(r"<[^>]+>", "", m.group(2)).strip() + "\n\n", s)
    s = re.sub(r'(?is)<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>', lambda m: f"[{re.sub(r'<[^>]+>', '', m.group(2))}]({m.group(1)})", s)
    s = re.sub(r"(?is)<li[^>]*>", "\n- ", s)
    s = re.sub(r"(?is)<tr[^>]*>", "\n| ", s)
    s = re.sub(r"(?is)</?(p|div|br|section|article|ul|ol|table|blockquote)[^>]*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return htmllib.unescape(s)


def syllables(w):
    w = w.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


CLAIM_RE = re.compile(r"\d[\d,.]*\s?%|\$\s?\d|\b\d+(?:\.\d+)?x\b|\b\d[\d,.]*\s(?:times|percent)\b|"
                      r"\b(?:studies|research|data|surveys?) (?:show|shows|suggest|suggests|found|finds)\b", re.I)
LINK_NEAR_RE = re.compile(r"\]\(https?://|https?://|<a\s", re.I)


def unsourced_claims(paragraphs):
    """Sentences with a number-like claim whose paragraph carries no link."""
    out = []
    for para in paragraphs:
        if para.lstrip().startswith("|") or LINK_NEAR_RE.search(para):
            continue
        for sent in re.split(r"(?<=[.!?])\s+", para):
            if CLAIM_RE.search(sent):
                out.append(strip_md(sent).strip()[:200])
    return out


def grade_text(raw, keyword=None, page_type="blog", is_html=False, brand=None):
    if is_html:
        meta = analyze_html(raw, "file://draft")
        fm = {"title": meta["title"], "description": meta["meta_description"]}
        body = html_to_md(raw)
    else:
        fm, body = split_frontmatter(raw)
    heads, paras, lists, tables, links = md_structure(body)
    plain = strip_md("\n".join(p for p in paras if p))
    ws = words(plain)
    wc = len(ws)
    h1 = [t for lvl, t in heads if lvl == 1]
    h2 = [t for lvl, t in heads if lvl == 2]
    title = fm.get("title") or (h1[0] if h1 else "")
    desc = fm.get("description") or fm.get("meta_description") or ""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", plain) if words(s)]
    avg_sent = round(wc / max(1, len(sentences)), 1)
    syl = sum(syllables(w) for w in ws)
    flesch = round(206.835 - 1.015 * (wc / max(1, len(sentences))) - 84.6 * (syl / max(1, wc)), 1) if wc else 0
    text_paras = [p for p in paras if p]
    long_paras = sum(1 for p in text_paras if len(words(p)) > 120)
    # passages: words between one heading and the next
    sections, cur = [], []
    for p in paras:
        if p is None:
            if cur:
                sections.append(len(words(strip_md(" ".join(cur)))))
            cur = []
        else:
            cur.append(p)
    if cur:
        sections.append(len(words(strip_md(" ".join(cur)))))
    citable = sum(1 for n in sections if PASSAGE_MIN <= n <= PASSAGE_MAX + 60)
    long_sections = sum(1 for n in sections if n > 300)
    summary_box = bool(re.search(r"^#{2,4}\s*(key takeaways|tl;dr|the bottom line|at a glance|summary|quick answer)",
                                 body, re.I | re.M))
    claims = unsourced_claims([p for p in paras if p])
    question_heads = sum(1 for t in h2 if t.rstrip().endswith("?"))
    ext = [l for l in links if l.startswith("http")]
    internal = [l for l in links if not l.startswith("http") and not l.startswith("#")]
    em = raw.count("\u2014") + len(re.findall(r"\s--\s", raw))
    placeholders = re.findall(r"\{\{[^}]+\}\}|\[Client to provide\]|\bTODO\b|\bTK\b|lorem ipsum", raw, re.I)
    r = {"word_count": wc, "title": title, "title_length": len(title), "meta_description": desc,
         "meta_description_length": len(desc), "h1": h1, "h2_count": len(h2), "question_h2": question_heads,
         "lists": lists, "table_rows": tables, "links_external": len(ext), "links_internal": len(internal),
         "avg_sentence_words": avg_sent, "flesch_reading_ease": flesch, "long_paragraphs": long_paras,
         "sections": len(sections), "citable_sections": citable, "long_sections": long_sections,
         "summary_box": summary_box, "unsourced_claims": claims[:20],
         "fk_grade": round(0.39 * (wc / max(1, len(sentences))) + 11.8 * (syl / max(1, wc)) - 15.59, 1) if wc else 0,
         "em_dashes": em,
         "placeholders": sorted(set(placeholders))}
    f = []
    need = MIN_WORDS.get(page_type, 300)
    if wc < need:
        f.append(flag("medium", "short", f"{wc} words; {page_type} pages usually need about {need}+ to cover the topic. Floor, not target."))
    if not title:
        f.append(flag("high", "title_missing", "No title (frontmatter `title:` or an H1)."))
    elif not (TITLE_MIN <= len(title) <= TITLE_MAX):
        f.append(flag("medium", "title_length", f"Title is {len(title)} chars; aim {TITLE_MIN}-{TITLE_MAX}."))
    if not desc:
        f.append(flag("medium", "desc_missing", "No meta description (frontmatter `description:`)."))
    elif not (DESC_MIN <= len(desc) <= DESC_MAX):
        f.append(flag("low", "desc_length", f"Meta description is {len(desc)} chars; aim {DESC_MIN}-{DESC_MAX}."))
    title_is_h1 = not is_html and fm.get("title") and not h1   # CMS renders the title as the H1
    if len(h1) > 1 or (not h1 and not title_is_h1):
        f.append(flag("medium", "h1_count", f"{len(h1)} H1 headings; use exactly one."))
    if len(h2) < 2 and wc > 400:
        f.append(flag("medium", "few_h2", "Fewer than 2 H2 sections; hard to skim and hard for AI to quote."))
    if long_paras:
        f.append(flag("low", "long_paragraphs", f"{long_paras} paragraphs over 120 words; break them up."))
    if avg_sent > 25:
        f.append(flag("low", "long_sentences", f"Average sentence is {avg_sent} words; aim under 20."))
    if em:
        f.append(flag("high", "em_dash", f"{em} em dashes (or spaced --). House rule: none in client-facing copy."))
    if long_sections:
        f.append(flag("medium", "long_sections", f"{long_sections} sections run over 300 words without a heading; split them."))
    if claims:
        f.append(flag("medium", "unsourced_claims",
                      f"{len(claims)} numeric or 'studies show' claims with no link in the same paragraph. Source them or cut them."))
    if brand and page_type == "blog":
        mentions = len(re.findall(r"\b" + re.escape(brand.lower()) + r"\b", plain.lower()))
        r["brand_mentions"] = mentions
        if mentions > 2:
            f.append(flag("low", "self_promotion", f"Brand named {mentions} times; informational posts read better with 1-2 plus the CTA."))
    if placeholders:
        f.append(flag("high", "placeholders", f"Unfilled placeholders: {', '.join(sorted(set(placeholders)))}"))
    if wc > 600 and not internal:
        f.append(flag("low", "no_internal_links", "No internal links to the owner's other pages."))
    if keyword:
        kw = keyword.lower()
        first100 = " ".join(ws[:100]).lower()
        kw_words = len(words(keyword)) or 1
        hits = len(re.findall(r"\b" + re.escape(kw) + r"\b", plain.lower()))
        density = round(100 * hits * kw_words / max(1, wc), 2)
        r["keyword"] = {"keyword": keyword, "in_title": kw in title.lower(), "in_h1": any(kw in t.lower() for t in h1),
                        "in_first_100_words": kw in first100, "in_an_h2": any(kw in t.lower() for t in h2),
                        "in_meta_description": kw in desc.lower(), "occurrences": hits, "density_pct": density}
        k = r["keyword"]
        if not k["in_title"]:
            f.append(flag("high", "kw_title", "Keyword is not in the title."))
        if h1 and not k["in_h1"]:
            f.append(flag("medium", "kw_h1", "Keyword is not in the H1."))
        if not k["in_first_100_words"]:
            f.append(flag("medium", "kw_intro", "Keyword does not appear in the first 100 words."))
        if desc and not k["in_meta_description"]:
            f.append(flag("low", "kw_desc", "Keyword is not in the meta description."))
        if density > KEYWORD_DENSITY_MAX and wc >= 300:
            f.append(flag("high", "kw_stuffing", f"Keyword density {density}%; over {KEYWORD_DENSITY_MAX}% reads as stuffing."))
        if hits == 0:
            f.append(flag("high", "kw_absent", "Keyword never appears in the body."))
    r["flags"] = f
    return r


def cmd_text(a):
    p = Path(a.file).expanduser()
    if not p.exists():
        die(f"No such file: {p}")
    raw = p.read_text(encoding="utf-8")
    r = grade_text(raw, a.keyword, a.type, p.suffix.lower() in (".html", ".htm"), a.brand)
    r["file"] = str(p)
    emit(r, a.json, print_text)
    return 1 if any(f["severity"] in ("critical", "high") for f in r["flags"]) else 0



# ---------- local: NAP consistency ----------

ADDR_ABBR = {"street": "st", "avenue": "ave", "road": "rd", "drive": "dr", "boulevard": "blvd", "lane": "ln",
             "court": "ct", "place": "pl", "parkway": "pkwy", "highway": "hwy", "suite": "ste", "building": "bldg",
             "north": "n", "south": "s", "east": "e", "west": "w", "floor": "fl", "apartment": "apt", "unit": "ste",
             "#": "ste"}


def norm_text(t):
    return " ".join(re.sub(r"[^\w\s#]", " ", t.lower()).split())


def norm_addr(t):
    return " ".join(ADDR_ABBR.get(w, w) for w in norm_text(t.replace("#", " # ")).split())


def norm_phone(t):
    d = re.sub(r"\D", "", t or "")
    return d[-10:] if len(d) >= 10 else d


def page_nap(url):
    f = fetch(url)
    if f.error or f.status != 200:
        return {"url": url, "error": f.error or f"HTTP {f.status}"}
    pp = PageParser()
    pp.feed(f.text)
    text = " ".join("".join(pp.text_parts).split())
    _, _, nodes = schema_types(pp.jsonld)
    local = [n for n in nodes if set(n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type")]) & (LOCAL_TYPES | {"Organization"})]
    phones = {norm_phone(m.group(0)) for m in PHONE_RE.finditer(text)}
    phones |= {norm_phone(h[4:]) for h, _, _ in pp.anchors if h.lower().startswith("tel:")}
    s_names = [str(n.get("name", "")) for n in local if n.get("name")]
    s_phones = {norm_phone(str(n.get("telephone", ""))) for n in local if n.get("telephone")}
    s_addrs = []
    for n in local:
        a = n.get("address")
        if isinstance(a, dict):
            s_addrs.append(" ".join(str(a.get(k, "")) for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode")))
        elif isinstance(a, str):
            s_addrs.append(a)
    return {"url": f.final_url, "text": text, "phones": sorted(p for p in phones if len(p) == 10),
            "schema_names": s_names, "schema_phones": sorted(s_phones), "schema_addresses": s_addrs,
            "business_site": ".business.site" in f.text, "google_chat_cta": bool(re.search(r"message us on google|google business (chat|messages)", text, re.I))}


def street_line(addr):
    """First comma-separated part: '12 Main St, Ste 4, Denver CO' -> '12 main st'."""
    return norm_addr(addr.split(",")[0])


def cmd_nap(a):
    out = {"owner": {"name": a.name, "address": a.address, "phone": a.phone}, "pages": [], "flags": []}
    want_phone = norm_phone(a.phone) if a.phone else None
    want_street = street_line(a.address) if a.address else None
    for u in a.urls:
        r = page_nap(normalize_url(u))
        if "error" in r:
            out["pages"].append(r)
            out["flags"].append(flag("high", "fetch", f"{u}: {r['error']}"))
            continue
        text_n, text_a = norm_text(r["text"]), norm_addr(r["text"])
        row = {"url": r["url"], "phones_found": r["phones"], "schema_names": r["schema_names"],
               "schema_phones": r["schema_phones"], "schema_addresses": r["schema_addresses"]}
        if a.name:
            row["name_in_text"] = norm_text(a.name) in text_n
            bad = [n for n in r["schema_names"] if norm_text(n) != norm_text(a.name)]
            if bad:
                out["flags"].append(flag("critical", "nap_name", f"{r['url']}: schema name {bad[0]!r} differs from {a.name!r}."))
            if not row["name_in_text"]:
                out["flags"].append(flag("medium", "nap_name_text", f"{r['url']}: business name {a.name!r} not found in the page text."))
        if want_street:
            row["address_in_text"] = want_street in text_a
            bad = [x for x in r["schema_addresses"] if want_street not in norm_addr(x)]
            if bad:
                out["flags"].append(flag("high", "nap_address", f"{r['url']}: schema address {bad[0]!r} does not match {a.address!r}."))
            if not row["address_in_text"]:
                out["flags"].append(flag("high", "nap_address_text", f"{r['url']}: street address {a.address!r} not found in the page text."))
        if want_phone:
            row["phone_in_page"] = want_phone in r["phones"]
            if not row["phone_in_page"]:
                out["flags"].append(flag("medium", "nap_phone", f"{r['url']}: phone {a.phone} not found (found: {', '.join(r['phones']) or 'none'})."))
            bad = [x for x in r["schema_phones"] if x != want_phone]
            if bad:
                out["flags"].append(flag("medium", "nap_phone_schema", f"{r['url']}: schema telephone differs ({bad[0]})."))
            others = [x for x in r["phones"] if x != want_phone]
            if others:
                out["flags"].append(flag("info", "nap_other_phones", f"{r['url']}: other numbers on the page: {', '.join(others)}. Fine if intentional (fax, tracking)."))
        if r["business_site"]:
            out["flags"].append(flag("medium", "business_site", f"{r['url']}: links to a *.business.site page (shut down 2024)."))
        if r["google_chat_cta"]:
            out["flags"].append(flag("medium", "google_chat", f"{r['url']}: mentions Google Business messaging/chat, which Google shut down in 2024."))
        out["pages"].append(row)
    emit(out, a.json, print_nap)
    return 0


# ---------- local: Google Business Profile completeness ----------

GBP_FIELDS = {
    "critical": ["primary_category", "additional_categories", "business_name", "address", "phone", "website",
                 "hours", "verified"],
    "important": ["description", "services", "products", "photos", "photo_recency", "attributes", "service_areas",
                  "menu_or_services_link"],
    "supplementary": ["posts", "post_recency", "booking_link", "social_profiles", "logo", "cover_photo", "videos",
                      "review_responses", "qa"],
}
GBP_MULT = {
    "general": {},
    "professional": {"services": 2, "description": 1.5, "photos": 0.5},
    "legal": {"description": 1.5, "services": 2, "photos": 0.5},
    "healthcare": {"hours": 1.5, "attributes": 1.5, "services": 2},
    "home_services": {"service_areas": 2, "hours": 1.5, "photos": 1.5},
    "restaurant": {"menu_or_services_link": 2, "photos": 1.5, "booking_link": 1.5, "attributes": 1.5},
    "real_estate": {"photos": 2, "social_profiles": 1.5, "posts": 1.5},
    "automotive": {"products": 2, "photos": 2, "services": 1.5},
}


def gbp_score(answers, industry="general"):
    mult = GBP_MULT[industry]
    got = mx = 0.0
    missing, partial, unknown = [], [], []
    for tier, fields in GBP_FIELDS.items():
        for fld in fields:
            v = answers.get(fld)
            if v in (None, ""):
                unknown.append(fld)
                continue
            if v == "na":
                continue
            v = int(v)
            if v not in (0, 1, 2):
                raise ValueError(f"{fld}: use 0 (missing), 1 (present), 2 (present and optimized) or \"na\"")
            m = mult.get(fld, 1)
            got += v * m
            mx += 2 * m
            if v == 0:
                missing.append((tier, fld))
            elif v == 1:
                partial.append((tier, fld))
    score = round(100 * got / mx) if mx else 0
    band = ("Excellent" if score >= 90 else "Good" if score >= 75 else "Needs work" if score >= 50
            else "Poor" if score >= 25 else "Critical")
    return {"score": score, "band": band, "industry": industry, "missing": missing, "partial": partial,
            "unknown": unknown}


def cmd_gbp(a):
    try:
        answers = json.loads(Path(a.file).expanduser().read_text(encoding="utf-8"))
        r = gbp_score(answers, a.industry)
    except (OSError, ValueError) as e:
        die(f"gbp: {e}")
    emit(r, a.json, print_gbp)
    return 0


# ---------- blog: traffic decay from Search Console exports ----------

def read_gsc_csv(path, metric):
    import csv
    with open(Path(path).expanduser(), encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    cols = {c.lower().strip(): c for c in rows[0].keys()}
    key = next((cols[c] for c in cols if "page" in c or c in ("url", "address")), None)
    val = next((cols[c] for c in cols if c.startswith(metric)), None)
    if not key or not val:
        die(f"{path}: need a page/URL column and a '{metric}' column (Search Console > Performance > Pages > Export).")
    out = {}
    for r in rows:
        try:
            out[r[key].strip()] = float(str(r[val]).replace(",", "") or 0)
        except ValueError:
            continue
    return out


def decay_report(cur, prev, min_prev=10):
    rows = []
    for page, before in prev.items():
        if before < min_prev:
            continue
        if page not in cur:
            rows.append({"page": page, "previous": before, "current": None, "change_pct": None, "status": "needs_validation"})
            continue
        now = cur[page]
        pct = round(100 * (now - before) / before, 1)
        drop = -pct
        status = ("critical" if drop >= 60 else "high" if drop >= 40 else "warning" if drop >= 20 else "stable")
        rows.append({"page": page, "previous": before, "current": now, "change_pct": pct, "status": status})
    order = {"critical": 0, "high": 1, "warning": 2, "needs_validation": 3, "stable": 4}
    rows.sort(key=lambda r: (order[r["status"]], -(r["previous"] - (r["current"] or 0))))
    return rows


def cmd_decay(a):
    cur, prev = read_gsc_csv(a.current, a.metric), read_gsc_csv(a.previous, a.metric)
    rows = decay_report(cur, prev, a.min)
    out = {"metric": a.metric, "total_current": sum(cur.values()), "total_previous": sum(prev.values()), "pages": rows}
    emit(out, a.json, print_decay)
    return 0

# ---------- output ----------

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def emit(obj, as_json, printer):
    if as_json:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        printer(obj)


def print_flags(flags, indent=""):
    for fl in sorted(flags, key=lambda x: SEV_ORDER.get(x["severity"], 9)):
        print(f"{indent}[{fl['severity'].upper()}] {fl['message']}")


def print_page(r):
    print(f"URL: {r['url']}  (HTTP {r.get('status')})")
    if r.get("error"):
        print(f"ERROR: {r['error']}")
        return
    print(f"Title ({r['title_length']}): {r['title']}")
    print(f"Meta description ({r['meta_description_length']}): {r['meta_description']}")
    print(f"H1: {' | '.join(r['h1']) or '(none)'}")
    print(f"Words: {r['word_count']}  Internal links: {r['links']['internal']}  External: {r['links']['external']}")
    im = r["images"]
    print(f"Images: {im['total']} (no alt: {im['missing_alt']}, empty alt: {im['empty_alt']}, no size: {im['missing_dimensions']})")
    print(f"Schema: {', '.join(r['schema_types']) or '(none)'}")
    print(f"Canonical: {r['canonical'] or '(none)'}  Robots: {r['robots'] or '(default)'}  Lang: {r['lang'] or '(none)'}")
    lo = r["local"]
    print(f"Local: LocalBusiness schema={lo['schema_local_business']} address={lo['schema_address']} "
          f"phone={lo['schema_phone']} hours={lo['schema_hours']} tel links={len(lo['tel_links'])} "
          f"phones in text={', '.join(lo['phones_in_text']) or 'none'} map embed={lo['google_map_embed']}")
    print("Headings:")
    for h in r["headings"][:30]:
        print(f"  {h}")
    print("Flags:")
    print_flags(r["flags"], "  ")


def print_site(o):
    print(f"Site: {o['final_origin']}  (checked {o['checked']})")
    if "http_redirects_to_https" in o:
        print(f"http -> https redirect: {'yes' if o['http_redirects_to_https'] else 'NO'}")
    rb = o.get("robots")
    if rb:
        print("robots.txt, homepage access:")
        for b, ok in rb["search_bots"].items():
            print(f"  {b:20} {'allowed' if ok else 'BLOCKED'}")
        for b in rb["ai_bots"]:
            print(f"  {b['bot']:20} {'allowed' if b['allowed'] else 'BLOCKED':8} ({b['owner']}, {b['kind']})")
    else:
        print("robots.txt: none")
    sm = o["sitemap"]
    print(f"Sitemap: {', '.join(sm['found']) or 'none'}  URLs: {sm['url_count']}  with lastmod: {sm['lastmod']}")
    print(f"llms.txt: {'present' if o['llms_txt']['present'] else 'none'}")
    print(f"Pages crawled: {o['summary']['pages_crawled']}  Links checked: {o['links_checked']}")
    for p in o["pages"]:
        c = count_flags(p.get("flags", []))
        cs = " ".join(f"{k}:{v}" for k, v in sorted(c.items(), key=lambda x: SEV_ORDER[x[0]]))
        print(f"  {p.get('status')} {p['url']}  words={p.get('word_count', '?')}  {cs}")
    print("Site flags:")
    print_flags(o["flags"], "  ")
    print("Most common page flags:")
    tally = {}
    for p in o["pages"]:
        for fl in p.get("flags", []):
            key = (fl["severity"], fl["code"])
            tally[key] = tally.get(key, 0) + 1
    for (sev, code), n in sorted(tally.items(), key=lambda x: (SEV_ORDER[x[0][0]], -x[1])):
        print(f"  [{sev.upper()}] {code}: {n} page(s)")


def print_speed(o):
    print(f"PageSpeed Insights ({o['strategy']}): {o['url']}")
    print(f"Performance score: {o['performance_score']}")
    if o["field"]:
        print(f"Real-user data (Chrome UX Report, {o['field_scope']}, 75th percentile):")
        for k, v in o["field"].items():
            print(f"  {k}: {v['p75']} -> {v['rating']}")
    else:
        print("Real-user data: none (not enough Chrome traffic). Lab numbers only; treat as a guide.")
    print("Lab:", ", ".join(f"{k}={v}" for k, v in o["lab"].items()))
    for op in o["opportunities"]:
        print(f"  save ~{op['savings_ms']}ms: {op['title']}")


def print_text(r):
    print(f"File: {r['file']}")
    print(f"Words: {r['word_count']}  H2: {r['h2_count']} (questions: {r['question_h2']})  "
          f"Lists: {r['lists']}  Links int/ext: {r['links_internal']}/{r['links_external']}")
    print(f"Title ({r['title_length']}): {r['title']}")
    print(f"Meta description ({r['meta_description_length']}): {r['meta_description']}")
    print(f"Avg sentence: {r['avg_sentence_words']} words  Flesch: {r['flesch_reading_ease']}  Grade: {r['fk_grade']}  "
          f"Sections: {r['sections']} (answer-sized: {r['citable_sections']}, over 300 words: {r['long_sections']})  "
          f"Summary box: {'yes' if r['summary_box'] else 'no'}")
    for c in r["unsourced_claims"]:
        print(f"  unsourced: {c}")
    if "keyword" in r:
        k = r["keyword"]
        print(f"Keyword '{k['keyword']}': title={k['in_title']} h1={k['in_h1']} first100={k['in_first_100_words']} "
              f"h2={k['in_an_h2']} meta={k['in_meta_description']} count={k['occurrences']} density={k['density_pct']}%")
    print("Flags:" if r["flags"] else "Flags: none")
    print_flags(r["flags"], "  ")
    blocking = [f for f in r["flags"] if f["severity"] in ("critical", "high")]
    print("GATE: FAIL (fix critical/high flags)" if blocking else "GATE: PASS")


def print_nap(o):
    ow = o["owner"]
    print(f"Owner's listing: {ow['name'] or '-'} | {ow['address'] or '-'} | {ow['phone'] or '-'}")
    for p in o["pages"]:
        if "error" in p:
            print(f"  {p['url']}: ERROR {p['error']}")
            continue
        print(f"  {p['url']}")
        print(f"    name in text: {p.get('name_in_text', '-')}  address in text: {p.get('address_in_text', '-')}  "
              f"phone on page: {p.get('phone_in_page', '-')}")
        print(f"    schema name: {', '.join(p['schema_names']) or '-'}  schema phone: {', '.join(p['schema_phones']) or '-'}")
        print(f"    schema address: {' / '.join(p['schema_addresses']) or '-'}")
    print("Flags:" if o["flags"] else "Flags: none (name, address and phone match everywhere checked)")
    print_flags(o["flags"], "  ")


def print_gbp(r):
    print(f"Google Business Profile completeness: {r['score']}/100 ({r['band']}), weighted for {r['industry']}")
    for label, items in (("Missing", r["missing"]), ("Present but not optimized", r["partial"])):
        if items:
            print(f"{label}:")
            for tier, fld in sorted(items):
                print(f"  [{tier}] {fld}")
    if r["unknown"]:
        print(f"Not answered (left out of the score): {', '.join(r['unknown'])}")


def print_decay(o):
    print(f"{o['metric']}: {o['total_previous']:.0f} -> {o['total_current']:.0f}")
    for r in o["pages"]:
        if r["status"] == "stable":
            continue
        ch = "gone from export" if r["current"] is None else f"{r['previous']:.0f} -> {r['current']:.0f} ({r['change_pct']}%)"
        print(f"  [{r['status'].upper()}] {r['page']}  {ch}")
    stable = sum(1 for r in o["pages"] if r["status"] == "stable")
    print(f"  {stable} pages stable or growing.")


# ---------- main ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--insecure", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("paths")
    p.add_argument("--business")
    p = sub.add_parser("page")
    p.add_argument("url")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("site")
    p.add_argument("url")
    p.add_argument("--max-pages", type=int, default=25)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("speed")
    p.add_argument("url")
    p.add_argument("--strategy", choices=["mobile", "desktop"], default="mobile")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("text")
    p.add_argument("file")
    p.add_argument("--keyword")
    p.add_argument("--type", choices=sorted(MIN_WORDS), default="blog")
    p.add_argument("--brand", help="business name, to count self-mentions in blog posts")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("nap", help="compare name/address/phone on pages with the owner's Google listing")
    p.add_argument("urls", nargs="+")
    p.add_argument("--name")
    p.add_argument("--address", help="street line first, e.g. '12 Main St, Ste 4, Denver, CO 80202'")
    p.add_argument("--phone")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("gbp", help="score a Google Business Profile from the owner's answers (JSON)")
    p.add_argument("file")
    p.add_argument("--industry", choices=sorted(GBP_MULT), default="general")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("decay", help="compare two Search Console 'Pages' CSV exports")
    p.add_argument("current")
    p.add_argument("previous")
    p.add_argument("--metric", choices=["clicks", "impressions"], default="clicks")
    p.add_argument("--min", type=float, default=10, help="ignore pages with fewer than this in the previous period")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    global INSECURE
    INSECURE = a.insecure
    if a.insecure:
        sys.stderr.write("NOTE: TLS verification is off for this run (--insecure).\n")
    if a.cmd == "paths":
        return cmd_paths(a) or 0
    if a.cmd == "page":
        r = analyze_url(normalize_url(a.url))
        emit(r, a.json, print_page)
        return 1 if r.get("error") else 0
    if a.cmd == "site":
        return cmd_site(a)
    if a.cmd == "speed":
        return cmd_speed(a)
    if a.cmd == "text":
        return cmd_text(a)
    if a.cmd == "nap":
        return cmd_nap(a)
    if a.cmd == "gbp":
        return cmd_gbp(a)
    if a.cmd == "decay":
        return cmd_decay(a)


if __name__ == "__main__":
    sys.exit(main())
