"""Offline tests for page_qa.py. Run from outside the skill dir:
python3 -m pytest <this dir> -q -p no:cacheprovider
Tests marked `chrome` skip cleanly when no Chrome/Chromium/Edge is installed."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "page_qa.py"
sys.path.insert(0, str(SCRIPT.parent))
import page_qa  # noqa: E402

CHROME = page_qa.find_chrome()
needs_chrome = pytest.mark.skipif(not CHROME, reason="no Chrome/Chromium/Edge found")

HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Roof Repair in Denver | Acme Roofing</title>
<meta name="description" content="Roof repair across the Denver metro.">
<link rel="stylesheet" href="styles.css"></head><body>"""

GOOD_BODY = """<h1>Roof repair in Denver</h1>
<p>Call <a href="tel:+13035550100">(303) 555-0100</a> for a free inspection.</p>
<img src="hero.jpg" alt="Crew on a roof">
<img src="line.svg" alt="" role="presentation">
<form action="https://formspree.io/f/abcd1234" method="POST">
  <label for="n">Name</label><input id="n" name="name" required>
  <label>Phone <input name="phone" type="tel" required></label>
  <input name="zip" aria-label="ZIP code" required>
  <input type="hidden" name="src" value="lp">
  <button type="submit">Book a free inspection</button>
</form>
</body></html>"""


def make_page(tmp_path, body, css="body{margin:0}", files=("hero.jpg", "line.svg"), head=HEAD):
    d = tmp_path / "site"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(head + body, encoding="utf-8")
    (d / "styles.css").write_text(css, encoding="utf-8")
    for f in files:
        (d / f).write_bytes(b"x")
    return d


def run(tmp_path, d, mode="draft", render=False):
    return page_qa.run_qa(str(d), mode=mode, out=str(tmp_path / "out" / "qa-report.md"), render=render)


def check(result, cid):
    return next(c for c in result["checks"] if c["id"] == cid)


# ---------------------------------------------------------------- static
def test_clean_page_passes(tmp_path):
    r = run(tmp_path, make_page(tmp_path, GOOD_BODY), mode="ship")
    for cid in ("placeholders", "lead_capture", "basics", "local_refs"):
        assert check(r, cid)["status"] == "PASS", (cid, check(r, cid))
    assert r["passed"] and r["exit_code"] == 0
    assert (tmp_path / "out" / "qa-report.md").is_file()
    # rendered checks were turned off: reported as WARN, never FAIL
    assert check(r, "overflow")["status"] == "WARN"


def test_placeholders_warn_in_draft_fail_in_ship(tmp_path):
    body = GOOD_BODY.replace("abcd1234", "REPLACE_ME").replace(
        "</body>", "<p>Lorem ipsum. TODO. Call [phone] or 000-000-0000. {{CITY}}</p>"
        '<a href="tel:+10000000000">x</a><a href="https://example.com/x">x</a></body>')
    d = make_page(tmp_path, body)
    draft = run(tmp_path, d, "draft")
    c = check(draft, "placeholders")
    assert c["status"] == "WARN" and draft["passed"]
    tokens = {i["token"] for i in c["items"]}
    assert {"REPLACE_ME", "lorem ipsum", "TODO", "[bracket placeholder]", "000-000 number",
            "{{template slot}}", "dummy tel: link", "example domain"} <= tokens
    ship = run(tmp_path, d, "ship")
    assert check(ship, "placeholders")["status"] == "FAIL" and ship["exit_code"] == 1


def test_replacement_is_not_replace_me(tmp_path):
    body = GOOD_BODY.replace("</body>", "<p>Full roof replacement, warranty on replacements.</p></body>")
    r = run(tmp_path, make_page(tmp_path, body), "ship")
    assert check(r, "placeholders")["status"] == "PASS"


def test_example_domain_in_input_hint_is_fine(tmp_path):
    body = GOOD_BODY.replace('<input id="n"', '<input placeholder="you@example.com" id="n"')
    r = run(tmp_path, make_page(tmp_path, body), "ship")
    assert check(r, "placeholders")["status"] == "PASS"


def test_placeholder_in_local_js_is_caught(tmp_path):
    body = GOOD_BODY.replace("</body>", '<script src="app.js"></script></body>')
    d = make_page(tmp_path, body)
    (d / "app.js").write_text('const ENDPOINT = "https://formspree.io/f/REPLACE_ME"; // TODO\n', encoding="utf-8")
    c = check(run(tmp_path, d, "ship"), "placeholders")
    assert c["status"] == "FAIL"
    assert [i["token"] for i in c["items"]] == ["REPLACE_ME"]   # TODO in JS code is not flagged


def test_no_way_to_convert_fails(tmp_path):
    body = "<h1>Hello</h1><p>We fix roofs.</p></body></html>"
    r = run(tmp_path, make_page(tmp_path, body, files=()), "draft")
    c = check(r, "lead_capture")
    assert c["status"] == "FAIL" and any("No way to convert" in i["message"] for i in c["items"])
    assert r["exit_code"] == 1


def test_mailto_only_is_a_way_to_convert_but_warns_no_tel(tmp_path):
    body = '<h1>Hello</h1><a href="mailto:hi@acme.test">Email us</a></body></html>'
    c = check(run(tmp_path, make_page(tmp_path, body, files=())), "lead_capture")
    assert c["status"] == "WARN"


def test_bad_form_wiring_fails(tmp_path):
    body = GOOD_BODY.replace('action="https://formspree.io/f/abcd1234" method="POST"', 'action="/submit"') \
                    .replace('aria-label="ZIP code" ', "")
    c = check(run(tmp_path, make_page(tmp_path, body)), "lead_capture")
    msgs = " ".join(i["message"] for i in c["items"] if i["status"] == "FAIL")
    assert c["status"] == "FAIL"
    assert "not an absolute http(s) URL" in msgs and "must be POST" in msgs and "'zip' has no label" in msgs


def test_data_endpoint_form_is_accepted(tmp_path):
    body = GOOD_BODY.replace('action="https://formspree.io/f/abcd1234" method="POST"',
                             'data-endpoint="https://hooks.example-crm.test/lead"')
    assert check(run(tmp_path, make_page(tmp_path, body)), "lead_capture")["status"] == "PASS"


def test_implausible_tel_fails(tmp_path):
    body = GOOD_BODY.replace("tel:+13035550100", "tel:123")
    c = check(run(tmp_path, make_page(tmp_path, body)), "lead_capture")
    assert c["status"] == "FAIL" and any("not a plausible" in i["message"] for i in c["items"])


def test_em_dash_fails_even_in_draft(tmp_path):
    body = GOOD_BODY.replace("for a free inspection.", "\u2014 free inspection, no pressure.")
    r = run(tmp_path, make_page(tmp_path, body), "draft")
    c = check(r, "basics")
    assert c["status"] == "FAIL" and any("em dash" in i["message"] for i in c["items"])
    assert r["exit_code"] == 1


def test_em_dash_entity_and_in_script_or_comment(tmp_path):
    body = GOOD_BODY.replace("</body>", "<!-- a \u2014 b --><script>var x='\u2014';</script></body>")
    assert check(run(tmp_path, make_page(tmp_path, body)), "basics")["status"] == "PASS"
    body2 = GOOD_BODY.replace("<h1>Roof repair in Denver</h1>", "<h1>Roof repair &mdash; Denver</h1>")
    assert check(run(tmp_path, make_page(tmp_path, body2)), "basics")["status"] == "FAIL"


def test_basics_failures(tmp_path):
    head = """<!doctype html><html><head><title></title></head><body>"""
    body = GOOD_BODY.replace("<h1>Roof repair in Denver</h1>", "<h1>A</h1><h1>B</h1>") \
                    .replace('alt="Crew on a roof"', "").replace(' role="presentation"', "") \
                    .replace("</body>", '<a href="#">Learn more</a></body>')
    c = check(run(tmp_path, make_page(tmp_path, body, head=head)), "basics")
    fails = " ".join(i["message"] for i in c["items"] if i["status"] == "FAIL")
    warns = " ".join(i["message"] for i in c["items"] if i["status"] == "WARN")
    assert "no lang" in fails and "viewport" in fails and "<title>" in fails
    assert "2 <h1>" in fails and "has no alt" in fails and "empty alt" in fails
    assert "meta description" in warns.lower() and 'href="#"' in warns


def test_empty_alt_inside_labelled_link_is_decorative(tmp_path):
    body = GOOD_BODY.replace("</body>", '<a href="/" aria-label="Acme home"><img src="hero.jpg" alt=""></a></body>')
    assert check(run(tmp_path, make_page(tmp_path, body)), "basics")["status"] == "PASS"


def test_missing_local_refs(tmp_path):
    css = "body{background:url('img/bg.png')} @import 'missing.css'; .x{background:url(data:image/png;base64,AA)}"
    body = GOOD_BODY.replace("</body>", '<script src="js/app.js"></script>'
                             '<img src="https://cdn.test/x.png" alt="x"><a href="privacy.html">Privacy</a></body>')
    c = check(run(tmp_path, make_page(tmp_path, body, css=css)), "local_refs")
    missing = {i["ref"] for i in c["items"]}
    assert c["status"] == "FAIL"
    assert missing == {"img/bg.png", "missing.css", "js/app.js", "privacy.html"}


def test_find_chrome_env_off(monkeypatch):
    monkeypatch.setenv("PAGE_QA_CHROME", "none")
    assert page_qa.find_chrome() is None


# ---------------------------------------------------------------- CLI
def cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8")


def test_cli_usage_errors(tmp_path):
    assert cli().returncode == 2
    assert cli(str(tmp_path / "nope")).returncode == 2
    assert cli(str(tmp_path), "--mode", "yolo").returncode == 2
    (tmp_path / "empty").mkdir()
    assert cli(str(tmp_path / "empty")).returncode == 2


def test_cli_json_and_exit_codes(tmp_path):
    d = make_page(tmp_path, GOOD_BODY.replace("abcd1234", "REPLACE_ME"))
    out = tmp_path / "rep" / "qa-report.md"
    p = cli(str(d / "index.html"), "--json", "--no-render", "--out", str(out))
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data["mode"] == "draft" and data["passed"] and len(data["checks"]) == 7
    assert out.is_file() and "Verdict:" in out.read_text(encoding="utf-8")
    p2 = cli(str(d), "--mode", "ship", "--no-render", "--out", str(out))
    assert p2.returncode == 1 and "FAIL" in p2.stdout


def test_report_has_no_em_dash(tmp_path):
    r = run(tmp_path, make_page(tmp_path, GOOD_BODY))
    assert "\u2014" not in Path(r["report"]).read_text(encoding="utf-8")


# ---------------------------------------------------------------- rendered
@needs_chrome
def test_overflow_detected_with_offender(tmp_path):
    body = GOOD_BODY.replace("</body>", '<div id="wide" style="width:600px;height:10px"></div></body>')
    r = page_qa.run_qa(str(make_page(tmp_path, body)), out=str(tmp_path / "out" / "r.md"))
    c = check(r, "overflow")
    assert c["status"] == "FAIL", c
    over = {i["message"].split(":")[0] for i in c["items"] if i["status"] == "FAIL"}
    assert over == {"375px"}
    assert "div#wide" in c["summary"] + " ".join(i["message"] for i in c["items"])
    assert r["exit_code"] == 1


@needs_chrome
def test_clean_page_renders_and_writes_shots(tmp_path):
    body = GOOD_BODY.replace("</body>", '<a href="#x" style="display:inline-block;width:20px;height:20px">i</a></body>')
    r = page_qa.run_qa(str(make_page(tmp_path, body)), out=str(tmp_path / "out" / "r.md"))
    assert check(r, "overflow")["status"] == "PASS"
    taps = check(r, "tap_targets")
    assert taps["status"] == "WARN" and taps["items"]
    assert check(r, "screenshots")["status"] == "PASS"
    for name in ("shot-1440.png", "shot-375.png"):
        png = (tmp_path / "out" / name).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes((tmp_path / "out" / "shot-1440.png").read_bytes()[16:20], "big")
    assert w == 1440


def test_placeholder_action_warns_in_draft_fails_in_ship(tmp_path):
    page = tmp_path / "index.html"
    page.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Real title</title></head>'
        '<body><h1>Hi</h1><form action="REPLACE_ME" method="POST"><label for="n">Name</label>'
        '<input id="n" name="n" required></form><a href="tel:+13035550123">Call</a>'
        '<svg><title>Decorative drawing</title></svg></body></html>', encoding="utf-8")
    draft = subprocess.run([sys.executable, str(SCRIPT), str(page), "--mode", "draft", "--no-render", "--json"],
                           capture_output=True, text=True)
    ship = subprocess.run([sys.executable, str(SCRIPT), str(page), "--mode", "ship", "--no-render", "--json"],
                          capture_output=True, text=True)
    assert draft.returncode == 0, draft.stdout
    assert ship.returncode == 1, ship.stdout
    assert "Real title" in draft.stdout and "Decorative drawing" not in draft.stdout.split("<title>")[-1][:200]
