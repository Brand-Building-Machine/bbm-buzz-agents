"""Offline tests for gads.py. Run from outside the skill dir: python3 -m pytest <this dir> -q -p no:cacheprovider"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gads.py"
sys.path.insert(0, str(SCRIPT.parent))
import gads  # noqa: E402

M = 1_000_000


def camp(cid, name, status="ENABLED", ctype="SEARCH", bidding="MAXIMIZE_CONVERSIONS", cost=0.0, conv=0.0, value=0.0,
         lost_budget=None, display=False, partners=False, geo="PRESENCE", shared=False, budget_rn=None, tcpa=None):
    c = {"id": cid, "name": name, "status": status, "advertisingChannelType": ctype, "biddingStrategyType": bidding,
         "networkSettings": {"targetContentNetwork": display, "targetPartnerSearchNetwork": partners},
         "geoTargetTypeSetting": {"positiveGeoTargetType": geo}}
    if tcpa:
        c["targetCpa"] = {"targetCpaMicros": str(int(tcpa * M))}
    m = {"costMicros": str(int(cost * M)), "conversions": conv, "conversionsValue": value, "clicks": "100", "impressions": "1000"}
    if lost_budget is not None:
        m["searchBudgetLostImpressionShare"] = lost_budget
    return {"campaign": c, "metrics": m,
            "campaignBudget": {"resourceName": budget_rn or f"b/{cid}", "amountMicros": str(50 * M), "explicitlyShared": shared}}


def kw(cid, agid, text, match="PHRASE", negative=False, cost=0.0, conv=0.0, impr=100, qs=None, comps=None, status="ENABLED"):
    q = {}
    if qs:
        q = {"qualityScore": qs, **(comps or {})}
    return {"campaign": {"id": cid, "name": f"c{cid}", "status": "ENABLED"},
            "adGroup": {"id": agid, "name": f"ag{agid}", "status": "ENABLED"},
            "adGroupCriterion": {"keyword": {"text": text, "matchType": match}, "status": status, "negative": negative,
                                 "qualityInfo": q},
            "metrics": {"costMicros": str(int(cost * M)), "conversions": conv, "impressions": str(impr)}}


def rsa(cid, agid, heads, descs=4, strength="GOOD", url="https://acme.example/roof-repair", ad_id=None, status="ENABLED"):
    return {"campaign": {"id": cid, "name": f"c{cid}", "status": "ENABLED"},
            "adGroup": {"id": agid, "name": f"ag{agid}", "status": "ENABLED"},
            "adGroupAd": {"status": status, "adStrength": strength, "policySummary": {"approvalStatus": "APPROVED"},
                          "ad": {"id": ad_id or f"{agid}1", "type": "RESPONSIVE_SEARCH_AD", "finalUrls": [url],
                                 "responsiveSearchAd": {"headlines": [{"text": h} for h in heads],
                                                        "descriptions": [{"text": f"d{i}"} for i in range(descs)]}}}}


def term(cid, text, cost, conv):
    return {"campaign": {"id": cid, "name": f"c{cid}"}, "adGroup": {"name": "ag"},
            "searchTermView": {"searchTerm": text, "status": "NONE"},
            "metrics": {"costMicros": str(int(cost * M)), "conversions": conv, "clicks": "5"}}


def write_data(tmp, **tables):
    d = tmp / "data"
    d.mkdir()
    base = {
        "account": [{"customer": {"autoTaggingEnabled": True, "timeZone": "America/Denver", "currencyCode": "USD"}}],
        "history": [{"segments": {"month": "2023-01-01"}, "metrics": {"costMicros": str(100 * M)}}],
        "campaigns": [], "keywords": [], "keywords_all": [], "search_terms": [], "ads": [], "ad_metrics": [],
        "campaign_assets": [], "customer_assets": [], "conversion_actions": [], "conversions_by_action": [],
        "campaign_criteria": [], "shared_sets": [], "campaign_shared_sets": [], "user_lists": [], "asset_groups": [],
        "change_events": [],
    }
    base.update(tables)
    for k, v in base.items():
        (d / f"{k}.json").write_text(json.dumps({"results": v}), encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"customer_id": "1234567890", "name": "Acme", "currency": "USD",
                                                 "days": 30, "start": "2026-08-01", "end": "2026-08-30",
                                                 "failures": {}}), encoding="utf-8")
    return d


def sig(res, sid):
    return next(s for s in res["signals"] if s["id"] == sid)


# ---------- pure helpers ----------

def test_negative_matching_rules():
    assert gads.kw_match_blocks("free", "BROAD", "free roof inspection")
    assert gads.kw_match_blocks("roof free", "BROAD", "free roof inspection")          # any order
    assert not gads.kw_match_blocks("free trial", "BROAD", "free roof inspection")     # needs all words
    assert gads.kw_match_blocks("roof inspection", "PHRASE", "free roof inspection")
    assert not gads.kw_match_blocks("inspection roof", "PHRASE", "free roof inspection")
    assert gads.kw_match_blocks("roof repair", "EXACT", "roof repair")
    assert not gads.kw_match_blocks("roof repair", "EXACT", "roof repair denver")


def test_parse_keyword_notation():
    assert gads.parse_kw("[roof repair]") == ("roof repair", "EXACT")
    assert gads.parse_kw('"roof repair"') == ("roof repair", "PHRASE")
    assert gads.parse_kw("roof repair") == ("roof repair", "BROAD")
    assert gads.parse_kw({"text": "roof repair", "match": "exact"}) == ("roof repair", "EXACT")


def test_budget_math():
    r = gads.budget_math(daily=50, cpc=5, cvr=0.05, lead_value=1000, close_rate=0.2)
    assert r["monthly"] == pytest.approx(1520)
    assert r["clicks_per_month"] == pytest.approx(304)
    assert r["conversions_per_month"] == pytest.approx(15.2)
    assert r["cpa"] == 100 and r["break_even_cpa"] == 200 and r["profitable_at_estimate"]
    assert "Maximize Conversions" in r["smart_bidding"]
    assert r["budget_for_30_conversions"] == 3000
    with pytest.raises(ValueError):
        gads.budget_math(daily=10, cpc=0)


def test_clean_id():
    assert gads.clean_id("123-456-7890") == "1234567890"
    with pytest.raises(SystemExit):
        gads.clean_id("12345")


# ---------- blueprint ----------

def good_blueprint():
    heads = ["Roof Repair in Denver", "Same Week Roof Repair", "Free Roof Inspection", "Hail Damage Experts",
             "Licensed and Insured", "Owner on Every Job", "Call for a Free Quote", "Family Owned Since 2009",
             "Leaks Fixed Fast", "Denver Roofers You Trust"]
    return {
        "business": "Acme Roofing", "goal": "leads", "currency": "USD", "brand_terms": ["acme"],
        "conversions": {"primary": [{"name": "Quote form", "category": "SUBMIT_LEAD_FORM", "counting": "ONE"}]},
        "economics": {"monthly_budget": 1520, "break_even_cpa": 200},
        "geo": {"type": "PRESENCE", "locations": ["Denver, CO"]},
        "negatives": {"account": ["jobs", '"how to"', "[acme]"]},
        "campaigns": [{
            "name": "Search | Roof Repair", "type": "SEARCH", "budget_daily": 50, "bidding": "MAXIMIZE_CONVERSIONS",
            "networks": {"search_partners": False, "display": False},
            "ad_groups": [{
                "name": "Roof repair", "landing_page": "https://acme.example/roof-repair",
                "keywords": ['"roof repair"', "[roof repair denver]", '"roof leak repair"'],
                "ads": [{"headlines": heads, "descriptions": ["We fix leaks fast. Free inspection.",
                                                              "Licensed Denver roofers since 2009.",
                                                              "Owner on every job, start to finish.",
                                                              "Call today for a same-week visit."]}],
            }],
        }],
        "assets": {"sitelinks": [{"text": f"Link {i}", "url": "https://acme.example/x"} for i in range(4)],
                   "callouts": ["Free Inspection", "Licensed", "Insured", "Family Owned"],
                   "snippets": [{"header": "Services", "values": ["Repair", "Replacement", "Inspection"]}],
                   "call": "+1 303 555 0100"},
    }


def test_blueprint_clean_passes():
    issues = gads.check_blueprint(good_blueprint())
    assert [i for i in issues if i[0] == "error"] == []


def test_blueprint_catches_problems():
    bp = good_blueprint()
    grp = bp["campaigns"][0]["ad_groups"][0]
    ad = grp["ads"][0]
    ad["headlines"][0] = "Roof Repair — Denver"                       # em dash
    ad["headlines"][1] = "This headline is far too long for Google"  # > 30
    ad["headlines"][2] = "Call Now!"                                  # exclamation
    ad["headlines"].append(ad["headlines"][3])                        # duplicate
    grp["keywords"].append("[acme roof repair]")
    bp["negatives"]["account"].append('"roof leak"')                  # blocks "roof leak repair"
    bp["campaigns"][0]["networks"]["display"] = True
    bp["conversions"]["primary"].append({"name": "Page view", "category": "PAGE_VIEW"})
    bp["geo"]["locations"] = []
    msgs = " | ".join(m for _, _, m in gads.check_blueprint(bp))
    for needle in ["em/en dash", "limit is 30", "'!'", "duplicate headline", "blocks your own keyword 'roof leak repair'",
                   "Display Network is on", "micro-event", "no locations"]:
        assert needle in msgs, needle


def test_blueprint_duplicate_keyword_across_groups():
    bp = good_blueprint()
    g2 = json.loads(json.dumps(bp["campaigns"][0]["ad_groups"][0]))
    g2["name"] = "Roof repair 2"
    bp["campaigns"][0]["ad_groups"].append(g2)
    msgs = [m for lvl, _, m in gads.check_blueprint(bp) if lvl == "error"]
    assert any("one home per keyword" in m for m in msgs)


def test_blueprint_render_has_notation_and_counts():
    md = gads.render_blueprint(good_blueprint())
    assert '"roof repair"' in md and "[roof repair denver]" in md
    assert "| 1 | Roof Repair in Denver | 21 |" in md
    assert "paused" in md.lower()
    assert "\u2014" not in md


def test_blueprint_cli_exit_codes(tmp_path):
    f = tmp_path / "bp.json"
    f.write_text(json.dumps(good_blueprint()), encoding="utf-8")
    ok = subprocess.run([sys.executable, str(SCRIPT), "blueprint", "check", str(f)], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bp = good_blueprint()
    bp["campaigns"][0]["budget_daily"] = 0
    f.write_text(json.dumps(bp), encoding="utf-8")
    bad = subprocess.run([sys.executable, str(SCRIPT), "blueprint", "check", str(f)], capture_output=True, text=True)
    assert bad.returncode == 1 and "no daily budget" in bad.stdout


# ---------- audit ----------

def test_audit_healthy_lead_account(tmp_path):
    heads = [f"Roof repair headline {i}" for i in range(12)]
    d = write_data(
        tmp_path,
        campaigns=[camp("1", "Search | Brand", cost=100, conv=10, lost_budget=0.02),
                   camp("2", "Search | Roof Repair", cost=1900, conv=40, lost_budget=0.05)],
        keywords_all=[kw("1", "10", "acme roofing", "EXACT"), kw("2", "20", "roof repair"), kw("2", "21", "roof leak")],
        keywords=[kw("2", "20", "roof repair", cost=1200, conv=30, qs=8), kw("2", "21", "roof leak", cost=700, conv=10, qs=7),
                  kw("1", "10", "acme roofing", "EXACT", cost=100, conv=10, qs=10)],
        search_terms=[term("2", "roof repair denver", 900, 25), term("2", "roof leak fix", 800, 15),
                      term("2", "roofing jobs", 40, 0), term("1", "acme roofing", 100, 10)],
        ads=[rsa("1", "10", [f"Acme Roofing {i}" for i in range(11)], url="https://acme.example/"),
             rsa("2", "20", heads, ad_id="201"), rsa("2", "20", heads[::-1], ad_id="202"),
             rsa("2", "21", [f"Leak fix {i}" for i in range(11)], ad_id="211"),
             rsa("2", "21", [f"Leak help {i}" for i in range(11)], ad_id="212"),
             rsa("1", "10", [f"Acme {i}" for i in range(11)], ad_id="102", url="https://acme.example/")],
        conversion_actions=[{"conversionAction": {"name": "Quote form", "category": "SUBMIT_LEAD_FORM", "type": "WEBPAGE",
                                                  "primaryForGoal": True, "includeInConversionsMetric": True,
                                                  "countingType": "ONE_PER_CLICK"}},
                            {"conversionAction": {"name": "Closed deal", "category": "CONVERTED_LEAD", "type": "UPLOAD_CLICKS",
                                                  "primaryForGoal": False, "includeInConversionsMetric": False}}],
        campaign_criteria=[{"campaign": {"id": c}, "campaignCriterion": {"type": t, "negative": n}}
                           for c in ("1", "2") for t, n in (("LOCATION", False), ("AD_SCHEDULE", False), ("KEYWORD", True))],
        shared_sets=[{"sharedSet": {"id": "9", "type": "NEGATIVE_KEYWORDS"}}],
        campaign_shared_sets=[{"campaign": {"id": c}, "sharedSet": {"id": "9", "type": "NEGATIVE_KEYWORDS"}} for c in ("1", "2")],
        customer_assets=[{"customerAsset": {"fieldType": f}} for f in ["SITELINK"] * 4 + ["CALLOUT"] * 4 + ["STRUCTURED_SNIPPET", "CALL"]],
        user_lists=[{"userList": {"type": "CRM_BASED", "sizeForSearch": "5000"}}],
    )
    res = gads.Audit(d, brand=["acme"], answers={"enhanced_conversions": "yes", "consent_mode": "na",
                                                 "exclude_customers": "yes"}).run().result()
    fails = [s for s in res["signals"] if s["status"] == "FAIL"]
    assert fails == [], fails
    assert res["account"]["goal"] == "leads" and res["account"]["maturity"] == "mature"
    assert res["grade"] == "A" and res["score"] >= 90
    assert sig(res, "3.1")["status"] == "PASS"
    assert sig(res, "14.1")["status"] == "PASS"         # brand ad groups may use the homepage
    assert res["ask_owner"] == []


def test_audit_catches_common_problems(tmp_path):
    d = write_data(
        tmp_path,
        campaigns=[camp("1", "Everything", bidding="MANUAL_CPC", cost=3000, conv=20, display=True,
                        geo="PRESENCE_OR_INTEREST", lost_budget=0.4),
                   camp("2", "Old test", cost=600, conv=0),
                   camp("3", "Paused shopping", status="PAUSED", ctype="SHOPPING", cost=500, conv=5)],
        keywords_all=[kw("1", "10", "acme roofing"), kw("1", "10", "roof repair", "BROAD"), kw("2", "20", "roof repair", "BROAD")],
        keywords=[kw("1", "10", "roof repair", "BROAD", cost=2000, conv=10, qs=3,
                     comps={"postClickQualityScore": "BELOW_AVERAGE"}),
                  kw("1", "10", "acme roofing", cost=1000, conv=10, qs=4, comps={"searchPredictedCtr": "BELOW_AVERAGE"})],
        search_terms=[term("1", "roofing jobs", 900, 0), term("1", "roof repair", 1500, 20), term("1", "diy roof", 600, 0)],
        ads=[rsa("1", "10", ["A", "B", "C"], descs=2, strength="POOR", url="https://acme.example/")],
        conversion_actions=[{"conversionAction": {"name": "Page view", "category": "PAGE_VIEW", "type": "WEBPAGE",
                                                  "primaryForGoal": True, "includeInConversionsMetric": True,
                                                  "countingType": "MANY_PER_CLICK"}},
                            {"conversionAction": {"name": "Form", "category": "SUBMIT_LEAD_FORM", "type": "WEBPAGE",
                                                  "primaryForGoal": True, "includeInConversionsMetric": True,
                                                  "countingType": "MANY_PER_CLICK"}}],
    )
    res = gads.Audit(d, goal="leads", brand=["acme"]).run().result()
    expect_fail = {"1.1", "2.1", "3.1", "5.1", "5.3", "6.1", "7.1", "7.2", "7.3", "9.2", "10.2", "10.3", "12.1", "12.3",
                   "13.1", "13.2"}
    got = {s["id"] for s in res["signals"] if s["status"] == "FAIL"}
    assert expect_fail <= got, expect_fail - got
    assert sig(res, "9.1")["status"] in ("WARN", "FAIL")        # 'roof repair' BROAD in two ad groups
    assert sig(res, "2.3")["status"] == "WARN"                  # lead counted every time
    assert sig(res, "11.1")["status"] == "FAIL" and sig(res, "11.1")["monthly_impact"] > 0
    assert res["zero_conversion_search_terms"][0]["term"] == "roofing jobs"
    assert sig(res, "5.3")["monthly_impact"] == pytest.approx(600 * 30.4 / 30, rel=0.01)
    assert "Paused shopping" in sig(res, "1.4")["evidence"]
    assert {q["key"] for q in res["ask_owner"]} >= {"enhanced_conversions", "exclude_customers"}
    assert res["grade"] == "C"


def test_audit_unknown_when_data_failed(tmp_path):
    d = write_data(tmp_path, campaigns=[camp("1", "S", cost=100, conv=5)])
    (d / "keywords_all.json").unlink()
    (d / "conversion_actions.json").unlink()
    mf = json.loads((d / "manifest.json").read_text())
    mf["failures"] = {"keywords_all": "boom", "conversion_actions": "boom"}
    (d / "manifest.json").write_text(json.dumps(mf))
    res = gads.Audit(d, brand=["x"]).run().result()
    assert sig(res, "9.1")["status"] == "UNKNOWN" and sig(res, "2.1")["status"] == "UNKNOWN"
    assert "keywords_all" in res["failed_data"]


def test_scoring_skips_unscored(tmp_path):
    d = write_data(tmp_path)
    au = gads.Audit(d, brand=["x"])
    au.add(1, "x", "a", "PASS", "")
    au.add(1, "y", "b", "FAIL", "")
    au.add(2, "z", "c", "ASK", "")
    au.add(3, "w", "d", "NA", "")
    per, overall = au.score()
    assert per == {1: 50.0} and overall == 50.0


def test_blueprint_compare(tmp_path):
    d = write_data(tmp_path, campaigns=[camp("1", "Search | Roof Repair", bidding="MANUAL_CPC", display=True)],
                   keywords_all=[kw("1", "10", "roof repair", "PHRASE"), kw("1", "10", "cheap roofs", "BROAD")])
    au = gads.Audit(d, brand=["acme"]).run()
    out = gads.compare_blueprint(au, good_blueprint())
    assert out["planned_keywords"] == 3 and out["live_keywords"] == 2
    assert any("roof repair denver" in m for m in out["planned_missing"])
    assert any("cheap roofs" in m for m in out["live_not_in_plan"])
    assert any("bidding MANUAL_CPC" in s for s in out["settings"])
    assert any("Display Network on" in s for s in out["settings"])


# ---------- composio wrapper ----------

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
url = args[1]
log = open(sys.argv[0] + ".log", "a"); log.write(json.dumps(args) + "\n"); log.close()
if not sys.stdin.isatty():
    data = sys.stdin.read()   # would block forever if stdin weren't closed by the caller
if "/v25/" in url:
    print("<!DOCTYPE html><html>404</html>"); sys.exit(0)
if "listAccessibleCustomers" in url:
    print(json.dumps({"resourceNames": ["customers/1112223333"]})); sys.exit(0)
body = json.loads(args[args.index("-d") + 1]) if "-d" in args else {}
if "9999999999" in url:
    print(json.dumps({"error": {"code": 403, "status": "PERMISSION_DENIED", "details": [{"errors": [
        {"errorCode": {"authorizationError": "USER_PERMISSION_DENIED"}, "message": "no"}]}]}})); sys.exit(0)
if body.get("pageToken") == "p2":
    print(json.dumps({"results": [{"n": 2}]})); sys.exit(0)
print(json.dumps({"results": [{"n": 1}], "nextPageToken": "p2"}))
'''


@pytest.fixture
def fake_composio(tmp_path, monkeypatch):
    f = tmp_path / "composio"
    f.write_text(FAKE, encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("COMPOSIO_BIN", str(f))
    monkeypatch.delenv("GOOGLE_ADS_API_VERSION", raising=False)
    monkeypatch.setattr(gads, "_version", [None])
    return f


@pytest.mark.skipif(os.name == "nt", reason="fake composio is a POSIX script")
def test_api_version_fallback_pagination_and_stdin(fake_composio):
    rows = gads.search("1112223333", "SELECT customer.id FROM customer", login="1112223333")
    assert rows == [{"n": 1}, {"n": 2}]
    assert gads._version[0] == "v24"                      # v25 answered HTML 404, fell back
    calls = [json.loads(ln) for ln in Path(str(fake_composio) + ".log").read_text().splitlines()]
    assert any("login-customer-id: 1112223333" in c for c in calls)


@pytest.mark.skipif(os.name == "nt", reason="fake composio is a POSIX script")
def test_api_error_explained(fake_composio):
    with pytest.raises(gads.ApiError) as e:
        gads.search("9999999999", "SELECT customer.id FROM customer")
    assert "USER_PERMISSION_DENIED" in str(e.value) and "--login" in str(e.value)


def test_missing_composio(monkeypatch):
    monkeypatch.setenv("COMPOSIO_BIN", "")
    monkeypatch.setattr(gads.shutil, "which", lambda _: None)
    with pytest.raises(SystemExit):
        gads.composio_bin()


def test_read_json_handles_utf16(tmp_path):
    f = tmp_path / "x.json"
    f.write_bytes(json.dumps({"a": 1}).encode("utf-16"))
    assert gads.read_json(f) == {"a": 1}


def test_no_machine_paths_or_ids_in_skill():
    root = SCRIPT.parents[1]
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".md", ".json") and p.name != "test_gads.py":
            text = p.read_text(encoding="utf-8")
            assert "/Users/" not in text and "C:\\Users" not in text, p
