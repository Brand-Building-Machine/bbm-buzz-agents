"""Offline tests for meta.py. Run from outside the skill dir:
    python3 -m pytest <abs path>/tests -q -p no:cacheprovider
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import meta  # noqa: E402

META = SCRIPTS / "meta.py"

AD_HEADER = ("Reporting starts,Reporting ends,Campaign name,Ad set name,Ad name,Ad delivery,"
             "Amount spent (USD),Leads,Impressions,Reach,Frequency,Link clicks\n")


def write(tmp, name, text):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    brand = tmp_path / "canon" / "brand"
    brand.mkdir(parents=True)
    cfg = {"OWNER_NAME": "Sam", "PROPOSED_PATH": str(tmp_path / "proposed"), "BRAND_PATH": str(brand)}
    cfg_path = tmp_path / "buzz-agents.config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("BUZZ_AGENTS_CONFIG", str(cfg_path))
    return tmp_path, brand, cfg_path


def run(*args, env=None):
    return subprocess.run([sys.executable, str(META), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, encoding="utf-8")


# ---------- numbers ----------

def test_num_parses_exports_and_never_guesses():
    assert meta.num("1,234.50") == 1234.5
    assert meta.num("$12") == 12
    assert meta.num("3.2%") == 3.2
    assert meta.num("") is None and meta.num("--") is None and meta.num("abc") is None


def test_tcpl_and_ceiling():
    assert meta.tcpl_from(600, 0.25) == 150
    assert meta.tcpl_from(600, 0) is None and meta.tcpl_from(600, 1.5) is None
    # $50/day, $40 TCPL: 50*14 / 80 = 8.75 -> 8 ads
    assert meta.ad_ceiling(50, 40) == 8
    assert meta.ad_ceiling(None, 40) is None


# ---------- audit ----------

def test_audit_verdicts_by_tcpl(tmp_path):
    rows = AD_HEADER + "\n".join([
        "2026-09-01,2026-09-14,Leads,Broad,Winner,active,300,10,20000,9000,2.2,400",
        "2026-09-01,2026-09-14,Leads,Broad,Too early,active,110,1,5000,4000,1.3,60",  # over fair-share floor (~96), under 3x TCPL
        "2026-09-01,2026-09-14,Leads,Broad,Dead concept,active,200,0,15000,8000,1.9,90",
        "2026-09-01,2026-09-14,Leads,Broad,Pricey,active,300,4,21000,8000,2.6,200",
        "2026-09-01,2026-09-14,Leads,Broad,Noise,active,240,5,18000,9000,2.0,210",
        "2026-09-01,2026-09-14,Leads,Broad,Never ran,active,0,0,0,0,,0",
    ]) + "\n"
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "ads.csv", rows)))
    a = meta.audit(rows_, level, bd, tcpl=40)
    v = {r["name"]: r["verdict"] for r in a["rows"]}
    assert level == "ad" and a["days"] == 14
    assert v["Winner"] == "winner"            # $30 per lead
    assert v["Too early"] == "wait"           # under 3x TCPL
    assert v["Dead concept"] == "swap"        # 5x TCPL, no leads
    assert v["Pricey"] == "swap"              # $75 > 1.5x
    assert v["Noise"] == "monitor"            # $48, within 1.5x
    assert v["Never ran"] == "kill"
    assert a["totals"]["leads"] == 20
    assert any("Learning limited" in n for n in a["notes"])     # ~10 leads/week
    assert any("qualified" in n.lower() for n in a["notes"])    # no CRM numbers


def test_audit_uses_qualified_leads(tmp_path):
    header = AD_HEADER.strip() + ",Qualified leads\n"
    rows = header + "\n".join([
        "2026-09-01,2026-09-14,L,B,Junk leads,active,300,20,1,1,1.5,1,4",        # 20% qualified
        "2026-09-01,2026-09-14,L,B,Middling,active,300,10,1,1,1.5,1,5",          # 50%
        "2026-09-01,2026-09-14,L,B,Good,active,300,10,1,1,1.5,1,8",              # 80%, $37.50/QL
        "2026-09-01,2026-09-14,L,B,Zero qual,active,300,10,1,1,1.5,1,0",
    ]) + "\n"
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "q.csv", rows)))
    v = {r["name"]: r for r in meta.audit(rows_, level, bd, tcpl=40)["rows"]}
    assert v["Junk leads"]["verdict"] == "swap" and "20%" in v["Junk leads"]["why"]
    assert v["Middling"]["verdict"] == "monitor"
    assert v["Good"]["verdict"] == "winner"
    assert v["Zero qual"]["verdict"] == "swap" and "angle" in v["Zero qual"]["why"]


def test_fair_share_kill_at_day_7(tmp_path):
    rows = AD_HEADER + "\n".join([
        "2026-09-01,2026-09-07,L,Broad,Starved,active,5,0,500,400,1.2,5",
        "2026-09-01,2026-09-07,L,Broad,Fed,active,200,6,15000,9000,1.6,150",
        "2026-09-01,2026-09-07,L,Retargeting,Small audience,active,20,1,900,300,3.0,9",
    ]) + "\n"
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "d7.csv", rows)))
    a = meta.audit(rows_, level, bd, tcpl=40)
    v = {r["name"]: r["verdict"] for r in a["rows"]}
    # Broad ad set spent 205 across 2 ads: fair share floor = 205/2 * 0.5 = 51.25
    assert v["Starved"] == "kill"
    assert v["Fed"] != "kill"
    # alone in its own ad set: low spend is the audience size, not Meta passing it over
    assert v["Small audience"] != "kill"


def test_no_fair_share_before_day_7(tmp_path):
    rows = AD_HEADER + "\n".join([
        "2026-09-01,2026-09-04,L,B,Slow start,active,5,0,500,400,1.2,5",
        "2026-09-01,2026-09-04,L,B,Fast start,active,200,6,15000,9000,1.6,150",
    ]) + "\n"
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "d4.csv", rows)))
    v = {r["name"]: r["verdict"] for r in meta.audit(rows_, level, bd, tcpl=40)["rows"]}
    assert v["Slow start"] == "wait"


def test_breakdown_rows_never_get_kill_verdicts(tmp_path):
    rows = ("Campaign name,Placement,Amount spent (USD),Leads,Impressions,Frequency\n"
            "Leads,Facebook Feed,400,4,30000,2.1\nLeads,Instagram Stories,50,2,4000,1.4\n")
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "bd.csv", rows)))
    a = meta.audit(rows_, level, bd, tcpl=40)
    assert bd == ["placement"]
    assert all(r["verdict"] == "info" for r in a["rows"])
    assert any("never recommend cutting" in n for n in a["notes"])


def test_results_that_are_not_leads_are_flagged(tmp_path):
    rows = ("Ad name,Amount spent (USD),Results,Result indicator\n"
            "Clicky,200,150,actions:link_click\n")
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "r.csv", rows)))
    a = meta.audit(rows_, level, bd, tcpl=40)
    assert a["rows"][0]["verdict"] == "check"


def test_summary_row_and_json_input(tmp_path):
    data = {"data": [{"ad_name": "A", "spend": "150", "leads": 5, "frequency": "4.5"},
                     {"ad_name": "Total", "spend": "150", "leads": 5}]}
    rows_, level, bd = meta.normalise(meta.read_rows(write(tmp_path, "x.json", json.dumps(data))))
    assert len(rows_) == 1 and level == "ad"
    a = meta.audit(rows_, level, bd, tcpl=40)
    assert "critical" in a["rows"][0]["fatigue"]


def test_warm_audiences_get_looser_frequency_band():
    row = {"name": "Retargeting - site visitors", "campaign": "", "frequency": 4.5}
    assert "warning" in meta.freq_flag(row)
    row["name"] = "Broad cold"
    assert "critical" in meta.freq_flag(row)


def test_audit_cli_reads_profile(workspace, tmp_path):
    _, brand, _ = workspace
    (brand / "meta-ads.json").write_text(json.dumps({"target_cpl": 40, "max_daily_budget": 30}), encoding="utf-8")
    f = write(tmp_path, "ads.csv", AD_HEADER + "2026-09-01,2026-09-14,L,B,Solo,active,300,10,1,1,2,1\n")
    r = run("audit", f)
    assert r.returncode == 0, r.stderr
    assert "WINNER" in r.stdout and "Target cost per qualified lead: 40.00" in r.stdout


# ---------- copy ----------

def test_copy_lint():
    clean = {"name": "ok", "primary_text": "Still paying too much for your team's health plan? Here's what changed this year.",
             "headline": "Get a free plan review", "description": "Takes 15 minutes"}
    assert meta.lint_copy(clean) == []
    bad = {"name": "bad", "primary_text": "Introducing our plan — the best!!!", "headline": "x" * 50,
           "description": "y" * 40}
    msgs = " ".join(m for _, m in meta.lint_copy(bad))
    assert "em dash" in msgs and "headline" in msgs and "description" in msgs and "Introducing" in msgs
    sev = dict((m.split(" ")[0], s) for s, m in meta.lint_copy(bad))
    assert sev["em"] == "error"


def test_personal_attributes_flagged_as_warning():
    ad = {"primary_text": "Are you in debt and can't sleep?", "headline": "", "description": ""}
    issues = meta.lint_copy(ad)
    assert any(s == "warn" and "personal attributes" in m for s, m in issues)
    ok = {"primary_text": "Debt piling up? Here's a plan that fits a real budget.", "headline": "", "description": ""}
    assert not any("personal attributes" in m for _, m in meta.lint_copy(ok))


def test_copy_cli_markdown(tmp_path):
    md = ("# Batch\n\n## Ad 1: review\n**Primary text:** Most owners overpay for benefits.\n"
          "**Headline:** Free plan review\n**Description:** 15 minutes\n\n"
          "## Ad 2: bad\nPrimary text: Our offer — now\nHeadline: Hi\n")
    f = write(tmp_path, "ads.md", md)
    r = run("copy", f)
    assert r.returncode == 1
    assert "Ad 1: review: clean" in r.stdout and "em dash" in r.stdout


# ---------- plans ----------

PROFILE = {"ad_account_id": "act_1234567", "page_id": "111", "lead_method": "instant_form",
           "target_cpl": 40, "max_daily_budget": 50, "special_ad_categories": [], "countries": ["US"],
           "qualified_lead_means": "business owner with 5+ staff"}


def create_plan(**over):
    plan = {
        "action": "create", "title": "Test", "account_id": "act_1234567",
        "campaign": {"name": "Leads - review offer", "objective": "OUTCOME_LEADS", "daily_budget": 30,
                     "special_ad_categories": []},
        "ad_set": {"name": "US broad", "optimization_goal": "LEAD_GENERATION", "destination": "instant_form",
                   "lead_form_id": "999", "targeting": {"countries": ["US"], "advantage_audience": True}},
        "ads": [{"name": "A1", "primary_text": "Most owners overpay for benefits. We check yours for free.",
                 "headline": "Free plan review", "description": "15 minutes", "asset": "a1.png"}],
    }
    plan.update(over)
    return plan


def test_clean_create_plan_passes():
    blocks, warns, risks = meta.check_plan(create_plan(), PROFILE)
    assert blocks == []
    assert any("PAUSED" in r for r in risks) and any("3000" in r for r in risks)   # cents shown


def test_create_blocks():
    p = create_plan()
    p["campaign"]["status"] = "ACTIVE"
    p["campaign"]["daily_budget"] = 80                      # over ceiling 50
    p["ad_set"]["optimization_goal"] = "LINK_CLICKS"
    p["ad_set"]["targeting"].update({"age_min": 30, "age_max": 55, "countries": ["US", "DE"]})
    p["ad_set"]["targeting"]["exclusions"] = {"interests": ["x"]}
    blocks, _, _ = meta.check_plan(p, PROFILE)
    text = " ".join(blocks)
    for needle in ("PAUSED", "ceiling", "does not match", "narrow ages", "dsa_beneficiary", "excluding interests"):
        assert needle in text, needle


def test_no_budget_ceiling_means_no_plan():
    prof = dict(PROFILE, max_daily_budget=None)
    blocks, _, _ = meta.check_plan(create_plan(), prof)
    assert any("max_daily_budget" in b for b in blocks)


def test_unknown_special_category_blocks():
    p = create_plan()
    p["campaign"].pop("special_ad_categories")
    blocks, _, _ = meta.check_plan(p, dict(PROFILE, special_ad_categories="unknown"))
    assert any("special ad category unknown" in b for b in blocks)
    ok, warns, _ = meta.check_plan(create_plan(campaign=dict(create_plan()["campaign"],
                                   special_ad_categories=["financial_products_services"])), PROFILE)
    assert ok == [] and any("special ad category set" in w for w in warns)


def test_website_leads_need_pixel_and_urls():
    p = create_plan()
    p["ad_set"]["destination"] = "website"
    blocks, _, _ = meta.check_plan(p, dict(PROFILE, pixel_id=""))
    assert any("pixel" in b for b in blocks) and any("url" in b for b in blocks)


def test_update_rules():
    p = {"action": "update", "account_id": "act_1234567", "changes": [
        {"target": "123", "field": "daily_budget", "before": 30, "after": 45},
        {"target": "124", "field": "status", "before": "PAUSED", "after": "ACTIVE"},
        {"target": "125", "field": "objective", "before": "OUTCOME_LEADS", "after": "OUTCOME_TRAFFIC"},
        {"target": "126", "field": "headline", "before": "a", "after": "b"}]}
    blocks, warns, risks = meta.check_plan(p, PROFILE)
    assert any("BUDGET UP" in r for r in risks)
    assert any("+50%" in w for w in warns) and any("resets its learning" in w for w in warns)
    assert any("activate" in b for b in blocks) and any("objective" in b for b in blocks)


def test_update_without_before_value_blocks():
    p = {"action": "update", "account_id": "act_1234567",
         "changes": [{"target": "1", "field": "daily_budget", "after": 40}]}
    blocks, _, _ = meta.check_plan(p, PROFILE)
    assert any("before" in b for b in blocks)


def test_activate_and_delete():
    blocks, _, risks = meta.check_plan({"action": "activate", "account_id": "act_1234567", "targets": ["1"]}, PROFILE)
    assert blocks == [] and any("STARTS SPENDING" in r for r in risks)
    blocks, _, _ = meta.check_plan({"action": "delete", "account_id": "act_1234567"}, PROFILE)
    assert blocks and "never" in blocks[0]


def test_wrong_account_blocks():
    blocks, _, _ = meta.check_plan(create_plan(account_id="act_7654321"), PROFILE)
    assert any("not the account" in b for b in blocks)


def test_plan_id_is_stable_and_changes_with_content():
    a, b = create_plan(), create_plan()
    assert meta.plan_id(a) == meta.plan_id(b)
    b["campaign"]["daily_budget"] = 31
    assert meta.plan_id(a) != meta.plan_id(b)
    before = meta.plan_id(a)
    meta.check_plan(a, PROFILE)
    assert meta.plan_id(a) == before          # checking never mutates the plan


def test_plan_cli_exit_codes(workspace, tmp_path):
    _, brand, _ = workspace
    (brand / "meta-ads.json").write_text(json.dumps(PROFILE), encoding="utf-8")
    good = write(tmp_path, "good.json", json.dumps(create_plan()))
    r = run("plan", good)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Ready for the owner" in r.stdout
    bad = create_plan()
    bad["campaign"]["daily_budget"] = 500
    r = run("plan", write(tmp_path, "bad.json", json.dumps(bad)))
    assert r.returncode == 1 and "BLOCKED" in r.stdout


# ---------- profile, paths, log ----------

def test_profile_init_check_and_never_overwrite(workspace):
    _, brand, _ = workspace
    r = run("profile", "init")
    assert r.returncode == 0 and (brand / "meta-ads.json").exists()
    r = run("profile", "check")
    assert r.returncode == 1 and "target_cpl" in r.stdout
    (brand / "meta-ads.json").write_text(json.dumps(PROFILE), encoding="utf-8")
    assert run("profile", "check").returncode == 0
    r = run("profile", "init")
    assert "not touched" in r.stdout
    assert json.loads((brand / "meta-ads.json").read_text())["page_id"] == "111"


def test_per_business_paths(tmp_path, monkeypatch):
    cfg = {"PROPOSED_PATH": str(tmp_path / "proposed"), "BRAND_PATH": str(tmp_path / "biz" / "{business}" / "brand")}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    env = {"BUZZ_AGENTS_CONFIG": str(p)}
    r = run("paths", env=env)
    assert r.returncode == 2 and "--business" in r.stderr
    r = run("paths", "--business", "acme", env=env)
    assert r.returncode == 0 and "meta-ads" in r.stdout and "acme" in r.stdout


def test_no_config_fails_loudly(tmp_path):
    env = {"BUZZ_AGENTS_CONFIG": str(tmp_path / "missing.json")}
    r = subprocess.run([sys.executable, str(META), "paths"], capture_output=True, text=True, cwd=tmp_path,
                       env={**os.environ, **env, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)})
    assert r.returncode == 2 and "workspace-config" in r.stderr


def test_log_appends(workspace, tmp_path):
    root, _, _ = workspace
    plan = write(tmp_path, "p.json", json.dumps(create_plan()))
    assert run("log", plan, "--result", "verified", "--ids", "c=1 s=2 a=3").returncode == 0
    assert run("log", plan, "--result", "unknown").returncode == 0
    log = (root / "proposed" / "meta-ads" / "launch-log.md").read_text(encoding="utf-8")
    assert log.count("result:") == 2 and "c=1 s=2 a=3" in log


def test_tcpl_cli():
    r = run("tcpl", "--cost-per-customer", "600", "--lead-to-customer", "0.25", "--daily-budget", "50")
    assert r.returncode == 0 and "150.00" in r.stdout and "Learning limited" in r.stdout


def test_no_private_paths_in_skill():
    root = Path(__file__).resolve().parents[1]
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".md") and f.name != "test_meta.py":
            text = f.read_text(encoding="utf-8")
            assert "/Users/" not in text and "waltclay" not in text.lower(), f
