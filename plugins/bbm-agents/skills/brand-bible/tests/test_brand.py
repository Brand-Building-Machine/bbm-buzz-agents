"""Offline tests for brand.py. Run: python3 -m pytest <this dir> -q"""
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "brand.py"


def run(cfg, *args):
    env = {"BUZZ_AGENTS_CONFIG": str(cfg), "PATH": "", "SYSTEMROOT": ""}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def cfg_for(tmp_path, brand_path):
    c = tmp_path / "cfg.json"
    c.write_text(json.dumps({"BRAND_PATH": str(brand_path)}), encoding="utf-8")
    return c


FILLED = {
    "brand-bible.md": """---
brand: "Acme Roofing"
---
# Acme Roofing: Brand Bible
## 1. The company
We replace and repair roofs in the Denver metro, mostly after hail. Family owned since 2009.
## 2. Offers
| Roof replacement (main) | Homeowners after hail | $12k-$25k | Owner on every inspection |
## 3. The customer
Homeowners 35-65 in Denver suburbs who just had a hailstorm and an adjuster visit.
#### Persona 1: Linda, 58
Retired teacher, worried about being scammed by storm chasers.
## 4. Positioning and proof
Local, owner-led, 4.9 stars from 212 Google reviews (Sep 2026). Not the cheapest.
## 5. Voice
Plain, specific, no pressure. Talk like the owner on a job site.
## 6. Visual identity
Clean and bright, real job photos, navy and orange. Never stock photos.
## 7. Compliance
No industry-specific rules. Standard truth-in-advertising: no invented reviews.
## 8. Open items
Licence number: [Client to provide] (owner). Nothing else outstanding right now.
""",
    "voice-agent.md": """# Voice
## 1. Brand DNA
Local roofers who tell you the truth about your roof.
## 2. Tone
| Plain | We'll tell you if you don't need a roof. | Industry-leading solutions |
## 3. Do and don't
Do name the town. Don't invent numbers.
## 4. Words
Use: roof, hail, inspection. Avoid: solutions.
## 5. Proprietary truths
1. Owner is on every inspection since 2009.
""",
    "offers.md": """# Offers
## Offer: Roof replacement
- What it is: full tear-off and replacement.
""",
    "root.css": """:root{--brand-primary:#1F3A5F;--brand-bg:#F7F5F2;--brand-ink:#1A1A1A;--brand-muted:#555555;
--brand-font-display:'Montserrat',sans-serif;--brand-font-body:'Inter',sans-serif;--brand-radius:8px;}
""",
}


def write_filled(d):
    d.mkdir(parents=True, exist_ok=True)
    for f, t in FILLED.items():
        (d / f).write_text(t, encoding="utf-8")


def test_no_config_exits_2(tmp_path):
    assert run(tmp_path / "nope.json", "paths").returncode == 2


def test_scaffold_creates_and_never_overwrites(tmp_path):
    d = tmp_path / "brand"
    c = cfg_for(tmp_path, d)
    r = run(c, "scaffold", "--name", "Acme Roofing")
    assert r.returncode == 0
    for f in ("brand-bible.md", "voice-agent.md", "offers.md", "root.css"):
        assert (d / f).exists()
    assert "Acme Roofing" in (d / "brand-bible.md").read_text(encoding="utf-8")
    (d / "offers.md").write_text("MINE", encoding="utf-8")
    run(c, "scaffold", "--name", "Other")
    assert (d / "offers.md").read_text(encoding="utf-8") == "MINE"


def test_blank_scaffold_fails_check(tmp_path):
    d = tmp_path / "brand"
    c = cfg_for(tmp_path, d)
    run(c, "scaffold", "--name", "Acme")
    r = run(c, "check")
    assert r.returncode == 1 and "unfilled placeholders" in r.stdout


def test_templates_have_no_em_dashes():
    tdir = SCRIPT.parents[1] / "templates"
    for f in tdir.iterdir():
        assert "—" not in f.read_text(encoding="utf-8"), f.name


def test_filled_set_passes_and_reports_open_items(tmp_path):
    d = tmp_path / "brand"
    write_filled(d)
    r = run(cfg_for(tmp_path, d), "check")
    assert r.returncode == 0, r.stdout
    assert "PASS" in r.stdout and "1 x '[Client to provide]'" in r.stdout


def test_check_catches_em_dash_missing_persona_bad_hex_low_contrast(tmp_path):
    d = tmp_path / "brand"
    write_filled(d)
    bible = (d / "brand-bible.md").read_text(encoding="utf-8")
    bible = bible.replace("#### Persona 1: Linda, 58", "Linda — 58")
    (d / "brand-bible.md").write_text(bible, encoding="utf-8")
    css = FILLED["root.css"].replace("#1F3A5F", "navy").replace("#555555", "#DDDDDD")
    (d / "root.css").write_text(css, encoding="utf-8")
    out = run(cfg_for(tmp_path, d), "check").stdout
    assert "em dashes" in out and "Persona" in out and "not a hex colour" in out and "4.5:1" in out


def test_per_business_paths_and_sheet(tmp_path):
    root = tmp_path / "businesses"
    c = cfg_for(tmp_path, root / "{business}" / "brand")
    assert run(c, "check").returncode == 2  # must name the business
    write_filled(root / "acme" / "brand")
    (root / "other").mkdir()
    out = run(c, "paths").stdout
    assert re.search(r"acme\s+has brand", out) and re.search(r"other\s+no brand yet", out)
    (root / "acme" / "brand" / "logo.svg").write_text("<svg/>", encoding="utf-8")
    r = run(c, "sheet", "--business", "acme")
    assert r.returncode == 0
    sheet = (root / "acme" / "brand" / "brand-sheet.html").read_text(encoding="utf-8")
    assert "Acme Roofing" in sheet and "#1F3A5F" in sheet and "logo.svg" in sheet and "Montserrat" in sheet
