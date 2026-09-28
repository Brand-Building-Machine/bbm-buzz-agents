"""Offline tests for seo.py. Run from outside the skill dir: python3 -m pytest <this dir> -q -p no:cacheprovider"""
import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seo.py"
sys.path.insert(0, str(SCRIPT.parent))
import seo  # noqa: E402

PAGE = """<!doctype html><html lang="en"><head>
<title>Roof Repair in Denver | Acme Roofing</title>
<meta name="description" content="Hail damage? Acme Roofing repairs and replaces roofs across the Denver metro. Owner on every inspection, free estimates, family owned since 2009.">
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="https://acme.example/">
<meta property="og:image" content="https://acme.example/og.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"RoofingContractor","name":"Acme Roofing","telephone":"+1-303-555-0100",
  "address":{"@type":"PostalAddress","streetAddress":"1 Main St","addressLocality":"Denver"},
  "openingHours":"Mo-Fr 08:00-17:00"},
 {"@type":"FAQPage","mainEntity":[]}]}</script>
<script type="application/ld+json">{not json}</script>
</head><body>
<h1>Roof repair in Denver</h1>
<p>Call <a href="tel:+13035550100">(303) 555-0100</a> for a free inspection.</p>
<h2>Why us</h2><p>We tell you the truth about your roof.</p>
<img src="a.jpg" alt="Crew on a roof" width="10" height="10"><img src="b.jpg">
<a href="/about">About</a><a href="/contact">Contact</a><a href="https://other.example/x" rel="nofollow">x</a>
<iframe src="https://www.google.com/maps/embed?pb=1"></iframe>
<script>var hidden = "script text is not content";</script>
</body></html>"""


def test_analyze_html_core_fields():
    r = seo.analyze_html(PAGE, "https://acme.example/")
    assert r["title"] == "Roof Repair in Denver | Acme Roofing"
    assert r["h1"] == ["Roof repair in Denver"]
    assert r["images"]["total"] == 2 and r["images"]["missing_alt"] == 1
    assert r["links"]["internal"] == 2 and r["links"]["external"] == 1 and r["links"]["nofollow"] == 1
    assert "RoofingContractor" in r["schema_types"] and "FAQPage" in r["schema_types"]
    assert len(r["schema_errors"]) == 1
    assert "script text" not in r["text_sample"]
    lo = r["local"]
    assert lo["schema_local_business"] and lo["schema_address"] and lo["schema_phone"] and lo["schema_hours"]
    assert lo["tel_links"] == ["+13035550100"] and lo["google_map_embed"]
    assert "(303) 555-0100" in lo["phones_in_text"]


def test_page_flags():
    codes = {f["code"] for f in seo.analyze_html(PAGE, "https://acme.example/")["flags"]}
    assert "schema_invalid" in codes          # broken JSON-LD block
    assert "schema_faqpage" in codes          # limited rich result, info only
    assert "img_alt" in codes
    assert "js_or_empty" in codes             # tiny body text
    assert "title_missing" not in codes and "h1_missing" not in codes


def test_noindex_and_missing_basics():
    html = '<html><head><meta name="robots" content="noindex"></head><body><p>hi</p></body></html>'
    codes = {f["code"] for f in seo.analyze_html(html, "http://x.example/")["flags"]}
    assert {"noindex", "no_https", "title_missing", "desc_missing", "h1_missing", "viewport_missing"} <= codes


def test_x_robots_header_noindex():
    r = seo.analyze_html("<html><title>t</title></html>", "https://x.example/", headers={"x-robots-tag": "noindex"})
    assert any(f["code"] == "noindex" for f in r["flags"])


def test_robots_ai_bots():
    txt = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\nSitemap: https://x.example/sm.xml\n"
    r = seo.robots_report(txt, "https://x.example")
    bots = {b["bot"]: b["allowed"] for b in r["ai_bots"]}
    assert bots["GPTBot"] is False and bots["OAI-SearchBot"] is True and bots["ClaudeBot"] is True
    assert r["search_bots"]["Googlebot"] is True
    assert r["sitemaps"] == ["https://x.example/sm.xml"]


def test_robots_block_all():
    r = seo.robots_report("User-agent: *\nDisallow: /\n", "https://x.example")
    assert r["all_bots_home_allowed"] is False and r["search_bots"]["Googlebot"] is False


def test_parse_sitemap():
    urlset = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://x/a</loc><lastmod>2026-01-01</lastmod></url><url><loc>https://x/b</loc></url></urlset>'
    assert seo.parse_sitemap(urlset) == ("urlset", ["https://x/a", "https://x/b"], 1)
    idx = b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://x/s1.xml</loc></sitemap></sitemapindex>'
    assert seo.parse_sitemap(idx)[0] == "index"
    assert seo.parse_sitemap(b"<html>nope")[0] == "invalid"


DRAFT = """---
title: "Employee Benefits for Small Businesses: A Plain Guide"
description: "What employee benefits a small business can offer, what they cost, and how to pick a plan without overpaying. Plain answers from a local broker."
---

## What employee benefits can a small business offer?

Employee benefits for a small business usually mean health, dental and vision cover plus a retirement plan. See [our plans](/plans).

## How much do they cost?

It depends \u2014 on headcount and plan. {{PRICE}}
"""


def test_grade_text_keyword_and_house_rules():
    r = seo.grade_text(DRAFT, "employee benefits", "blog")
    k = r["keyword"]
    assert k["in_title"] and k["in_first_100_words"] and k["in_an_h2"] and k["in_meta_description"]
    codes = {f["code"] for f in r["flags"]}
    assert "em_dash" in codes and "placeholders" in codes and "short" in codes
    assert "h1_count" not in codes            # frontmatter title stands in for the H1
    assert "kw_stuffing" not in codes         # too short to judge density
    assert r["question_h2"] == 2 and r["links_internal"] == 1


def test_grade_text_html_draft():
    html = "<html><head><title>Roof repair in Denver: what it costs in 2026</title></head><body><h1>Roof repair in Denver</h1><h2>Cost</h2><p>Roof repair in Denver costs...</p></body></html>"
    r = seo.grade_text(html, "roof repair in denver", "service", is_html=True)
    assert r["h1"] == ["Roof repair in Denver"] and r["keyword"]["in_h1"] and r["keyword"]["in_title"]


def test_text_cli_gate_exit_codes(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(DRAFT, encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPT), "text", str(bad)], capture_output=True, text=True)
    assert p.returncode == 1 and "GATE: FAIL" in p.stdout
    good = tmp_path / "good.md"
    body = " ".join(["Plain sentence about local roof repair costs and timing."] * 40)
    good.write_text('---\ntitle: "Roof Repair in Denver: Costs, Timing and What to Ask"\n'
                    'description: "What roof repair in Denver costs, how long it takes, and the three questions to ask any roofer before you sign anything at all."\n'
                    f"---\n\n## Costs\n\n{body}\n\n## Timing\n\n{body}\n\nSee [pricing](/pricing).\n", encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPT), "text", str(good), "--type", "page"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout


def test_parse_psi():
    data = {"lighthouseResult": {"categories": {"performance": {"score": 0.62}}, "audits": {
        "largest-contentful-paint": {"numericValue": 3200.4},
        "cumulative-layout-shift": {"numericValue": 0.031},
        "render-blocking-resources": {"score": 0.3, "title": "Eliminate render-blocking resources",
                                      "details": {"type": "opportunity", "overallSavingsMs": 900}}}},
        "loadingExperience": {"metrics": {
            "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2100},
            "INTERACTION_TO_NEXT_PAINT": {"percentile": 650},
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 12}}}}
    r = seo.parse_psi(data)
    assert r["performance_score"] == 62 and r["lab"]["LCP"] == 3200
    assert r["field"]["LCP"]["rating"] == "good" and r["field"]["INP"]["rating"] == "poor"
    assert r["field"]["CLS"] == {"p75": 0.12, "rating": "needs improvement"}
    assert r["opportunities"][0]["savings_ms"] == 900


def test_paths_uses_config(tmp_path):
    cfg = tmp_path / "cfg.json"
    brand = tmp_path / "brand"
    brand.mkdir()
    (brand / "voice-agent.md").write_text("x", encoding="utf-8")
    cfg.write_text(json.dumps({"PROPOSED_PATH": str(tmp_path / "proposed"), "BRAND_PATH": str(brand)}), encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPT), "paths"], capture_output=True, text=True,
                       env={"BUZZ_AGENTS_CONFIG": str(cfg), "PATH": "", "SYSTEMROOT": ""})
    assert p.returncode == 0
    assert str(tmp_path / "proposed" / "seo") in p.stdout
    assert "voice-agent.md: yes" in p.stdout and "brand-bible.md: MISSING" in p.stdout


def test_paths_without_config(tmp_path):
    p = subprocess.run([sys.executable, str(SCRIPT), "paths"], capture_output=True, text=True, cwd=tmp_path,
                       env={"BUZZ_AGENTS_CONFIG": str(tmp_path / "nope.json"), "PATH": "", "SYSTEMROOT": ""})
    assert p.returncode == 2 and "workspace-config" in p.stderr


# ---------- end to end against a local site (no internet) ----------

SITE = {
    "/": PAGE.replace("https://acme.example/", "/"),
    "/about": "<html lang='en'><head><title>About Acme Roofing, Denver roofers since 2009</title></head>"
              "<body><h1>About</h1><a href='/'>Home</a><a href='/gone'>Old page</a>"
              "<a href='/(303) 555 0100'>Call</a></body></html>",   # phone typed as a link: must not crash
    "/contact": "<html><head><title>About Acme Roofing, Denver roofers since 2009</title></head><body><h1>Contact</h1></body></html>",
    "/robots.txt": "User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n",
    "/llms.txt": "# Acme Roofing\n> Roofers in Denver.\n",
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = SITE.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain" if self.path.endswith(".txt") else "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *a):
        pass


@pytest.fixture()
def local_site():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_site_end_to_end(local_site):
    p = subprocess.run([sys.executable, str(SCRIPT), "site", local_site, "--max-pages", "5", "--json"],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout)
    codes = [f["code"] for f in o["flags"]]
    assert "robots_block_ai_search" in codes                     # OAI-SearchBot blocked
    assert "sitemap_missing" in codes
    assert o["llms_txt"]["present"] and o["llms_txt"]["starts_with_h1"]
    assert any(b["url"].endswith("/gone") for b in o["broken_internal_links"])
    assert "dup_title" in codes                                  # /about and /contact share a title
    assert o["summary"]["pages_crawled"] == 5                   # /, /about, /contact, and the 404s /gone and the phone link
    assert any("555" in b["url"] for b in o["broken_internal_links"])


def test_page_cli_fetch_error():
    p = subprocess.run([sys.executable, str(SCRIPT), "page", "http://127.0.0.1:9", "--json"],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 1
    assert json.loads(p.stdout)["flags"][0]["code"] == "fetch"


# ---------- checks added from the claude-seo audit ----------

def test_js_shell_and_hero_and_schema_hygiene():
    shell = ('<html><head><title>App</title><script src="/a.js"></script><script src="/b.js"></script>'
             '<script src="/c.js"></script><script type="application/ld+json">{"@type":"Organization","name":"[Business Name]"}</script>'
             '</head><body><div id="root"></div><img src="hero.jpg" loading="lazy" alt="x"></body></html>')
    r = seo.analyze_html(shell, "https://x.example/")
    codes = {f["code"] for f in r["flags"]}
    assert {"js_shell", "hero_lazy", "render_blocking"} <= codes
    errs = " ".join(r["schema_errors"])
    assert "no @context" in errs and "placeholder" in errs


def test_mixed_content_and_business_site():
    html = ('<html><body><img src="http://cdn.example/a.jpg" alt="a">'
            '<a href="https://acme.business.site/">old site</a></body></html>')
    codes = {f["code"] for f in seo.analyze_html(html, "https://x.example/")["flags"]}
    assert "mixed_content" in codes and "business_site" in codes


def test_unsourced_claims_and_spaced_double_hyphen():
    md = ("---\ntitle: t\n---\n\n## A\n\nStudies show 73% of owners overpay. Costs rose 12% "
          "([KFF](https://www.kff.org/x)).\n\n## B\n\nPremiums doubled -- again. Plans cost $500 a month.\n")
    r = seo.grade_text(md)
    assert r["unsourced_claims"] == ["Plans cost $500 a month."]   # paragraph A has a link, B does not
    assert r["em_dashes"] == 1


def test_gbp_score_and_multipliers():
    all2 = {f: 2 for tier in seo.GBP_FIELDS.values() for f in tier}
    assert seo.gbp_score(all2)["score"] == 100
    half = dict(all2, services=0)
    general = seo.gbp_score(half)["score"]
    pro = seo.gbp_score(half, "professional")["score"]
    assert pro < general                     # services weigh double for professional services
    r = seo.gbp_score({"primary_category": 2, "qa": "na", "phone": 1})
    assert r["score"] == 75 and ("critical", "phone") in r["partial"] and "hours" in r["unknown"]
    with pytest.raises(ValueError):
        seo.gbp_score({"photos": 3})


def test_decay(tmp_path):
    cur = tmp_path / "cur.csv"
    prev = tmp_path / "prev.csv"
    cur.write_text("Top pages,Clicks,Impressions\nhttps://x/a,30,900\nhttps://x/b,95,1000\nhttps://x/c,5,50\n", encoding="utf-8")
    prev.write_text("Top pages,Clicks,Impressions\nhttps://x/a,100,1000\nhttps://x/b,100,1000\nhttps://x/c,6,60\nhttps://x/d,\"1,200\",9000\n", encoding="utf-8")
    rows = seo.decay_report(seo.read_gsc_csv(cur, "clicks"), seo.read_gsc_csv(prev, "clicks"))
    by = {r["page"]: r["status"] for r in rows}
    assert by == {"https://x/a": "critical", "https://x/b": "stable", "https://x/d": "needs_validation"}  # c under --min


def test_norm_addr():
    assert seo.street_line("12 Main Street, Suite 4, Denver") == "12 main st"
    assert seo.norm_phone("(303) 555-0100") == seo.norm_phone("+1 303.555.0100") == "3035550100"


def test_nap_end_to_end(local_site):
    base = [sys.executable, str(SCRIPT), "nap", local_site + "/", "--json", "--name", "Acme Roofing"]
    ok = subprocess.run(base + ["--address", "1 Main Street, Denver", "--phone", "303-555-0100"],
                        capture_output=True, text=True, timeout=60)
    o = json.loads(ok.stdout)
    assert o["pages"][0]["phone_in_page"] is True
    codes = [f["code"] for f in o["flags"]]
    assert "nap_name" not in codes and "nap_address" not in codes and "nap_phone" not in codes
    bad = subprocess.run(base[:-2] + ["--name", "Acme Roofing LLC", "--address", "9 Elm St", "--phone", "303-555-9999"],
                         capture_output=True, text=True, timeout=60)
    codes = [f["code"] for f in json.loads(bad.stdout)["flags"]]
    assert {"nap_name", "nap_address", "nap_phone"} <= set(codes)
