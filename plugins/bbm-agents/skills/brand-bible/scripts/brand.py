#!/usr/bin/env python3
"""Brand bible helper. Stdlib only; macOS, Linux, Windows.

Reads BRAND_PATH from the owner's buzz-agents config (same lookup as the other skills).
BRAND_PATH may contain {business} when the owner runs several businesses.

  brand.py paths                         # where the brand folder(s) live; lists businesses if per-business
  brand.py scaffold --name "Acme Roofing" [--business acme] [--website URL]
                                         # create the folder + blank templates (never overwrites)
  brand.py sheet [--business acme]       # build brand-sheet.html from root.css (+ logo if present)
  brand.py check [--business acme]       # completeness gate; exit 1 if anything is missing

Exit codes: 0 ok, 1 check failed, 2 config/usage problem.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
FILES = ["brand-bible.md", "voice-agent.md", "offers.md", "root.css"]
BIBLE_SECTIONS = ["The company", "Offers", "The customer", "Positioning and proof",
                  "Voice", "Visual identity", "Compliance", "Open items"]
VOICE_SECTIONS = ["Brand DNA", "Tone", "Do and don't", "Words", "Proprietary truths"]
REQUIRED_VARS = ["--brand-primary", "--brand-bg", "--brand-ink", "--brand-muted",
                 "--brand-font-display", "--brand-font-body"]
MIN_SECTION_CHARS = 40
TBD = "[Client to provide]"
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
SLOT_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


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
    if not cfg.get("BRAND_PATH"):
        die("Config has no BRAND_PATH. Run workspace-config to add where brand folders live.")
    return cfg


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def brand_dir(cfg, business):
    pattern = cfg["BRAND_PATH"]
    if "{business}" in pattern:
        if not business:
            die("This workspace has one brand per business. Pass --business <name>. "
                "Run `brand.py paths` to see them.")
        return Path(pattern.replace("{business}", business)).expanduser()
    return Path(pattern).expanduser()


# ---------- helpers ----------

def body(text):
    """Text with frontmatter and HTML comments removed."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return COMMENT_RE.sub("", text)


def sections(text, level="##"):
    """{title: body} for headings like '## 3. The customer' or '## Brand DNA'."""
    out, cur, buf = {}, None, []
    pat = re.compile(rf"^{level} (?:\d+\.\s*)?(.+?)\s*$")
    for line in text.splitlines():
        m = pat.match(line)
        if m and not line.startswith(level + "#"):
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def css_vars(css):
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", COMMENT_RE.sub("", css))}


def luminance(hx):
    hx = hx.lstrip("#")
    if len(hx) == 3:
        hx = "".join(c * 2 for c in hx)
    rgb = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def brand_name(folder):
    bible = folder / "brand-bible.md"
    if bible.exists():
        m = re.search(r'^brand:\s*"?([^"\n]+)"?', bible.read_text(encoding="utf-8"), re.M)
        if m and "{{" not in m.group(1):
            return m.group(1).strip()
    return folder.name


# ---------- commands ----------

def cmd_paths(a):
    cfg = load_config()
    pattern = cfg["BRAND_PATH"]
    if "{business}" not in pattern:
        d = Path(pattern).expanduser()
        print(f"brand folder: {d} ({'exists' if d.exists() else 'not created yet'})")
        return
    print(f"one brand per business: {pattern}")
    head, _, tail = pattern.partition("{business}")
    parent = Path(head).expanduser()
    if parent.exists():
        for child in sorted(p for p in parent.iterdir() if p.is_dir()):
            target = Path(str(child) + tail)
            state = "has brand" if (target / "brand-bible.md").exists() else "no brand yet"
            print(f"  {child.name:30} {state}")


def cmd_scaffold(a):
    cfg = load_config()
    d = brand_dir(cfg, a.business)
    d.mkdir(parents=True, exist_ok=True)
    fills = {"{{BRAND_NAME}}": a.name, "{{WEBSITE}}": a.website or TBD,
             "{{DATE}}": dt.date.today().isoformat()}
    made, kept = [], []
    for f in FILES:
        target = d / f
        if target.exists():
            kept.append(f)
            continue
        text = (TEMPLATES / f).read_text(encoding="utf-8")
        for k, v in fills.items():
            text = text.replace(k, v)
        target.write_text(text, encoding="utf-8")
        made.append(f)
    print(f"brand folder: {d}")
    if made:
        print("created: " + ", ".join(made))
    if kept:
        print("already there, left untouched: " + ", ".join(kept))


SHEET = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}: Brand Sheet</title>
<link rel="stylesheet" href="root.css">
<style>
body{{margin:0;background:var(--brand-bg);color:var(--brand-ink);font-family:var(--brand-font-body);line-height:1.55}}
.wrap{{max-width:960px;margin:0 auto;padding:40px 20px}}
h1,h2,.display{{font-family:var(--brand-font-display);line-height:1.1;margin:0 0 12px}}
h1{{font-size:clamp(32px,6vw,52px)}} h2{{font-size:22px;margin-top:40px}}
.muted{{color:var(--brand-muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}}
.sw{{border-radius:var(--brand-radius,10px);overflow:hidden;border:1px solid rgba(0,0,0,.08);background:#fff}}
.sw i{{display:block;height:90px}} .sw div{{padding:10px 12px;font-size:13px;color:#222}}
.sw b{{display:block;font-family:ui-monospace,monospace;font-size:12px}}
.logo img{{max-height:90px;max-width:100%}}
.btn{{display:inline-block;background:var(--brand-primary);color:#fff;padding:12px 22px;border-radius:var(--brand-radius,10px);font-family:var(--brand-font-display);font-weight:700;text-decoration:none}}
.card{{background:var(--brand-surface,#fff);border:1px solid var(--brand-line,rgba(0,0,0,.1));border-radius:var(--brand-radius,10px);padding:20px;margin-top:12px}}
</style></head><body><div class="wrap">
<p class="muted">Brand sheet, generated from root.css. Edit root.css, then regenerate.</p>
<h1>{name}</h1>
{logo}
<h2>Colours</h2><div class="grid">{swatches}</div>
<h2>Type</h2>
<div class="card"><div class="display" style="font-size:36px">Display: {font_display}</div>
<p style="font-size:18px">Body: {font_body}. The quick brown fox jumps over the lazy dog. 0123456789</p></div>
<h2>In use</h2>
<div class="card"><h2 style="margin-top:0">A headline in the brand</h2>
<p class="muted">Secondary text in the muted colour.</p><a class="btn" href="#">Primary button</a></div>
</div></body></html>
"""


def cmd_sheet(a):
    cfg = load_config()
    d = brand_dir(cfg, a.business)
    css = d / "root.css"
    if not css.exists():
        die(f"No root.css in {d}. Fill it first.")
    v = css_vars(css.read_text(encoding="utf-8"))
    sw = []
    for k, val in v.items():
        if HEX_RE.match(val):
            label = k.replace("--brand-", "")
            sw.append(f'<div class="sw"><i style="background:{val}"></i><div>{html.escape(label)}<b>{val}</b></div></div>')
    logo = ""
    for cand in sorted(d.glob("logo*")):
        if cand.suffix.lower() in (".png", ".svg", ".jpg", ".jpeg", ".webp"):
            logo = f'<div class="logo"><img src="{html.escape(cand.name)}" alt="logo"></div>'
            break
    fam = lambda s: html.escape(s.split(",")[0].strip().strip("'\"")) if s else "not set"
    out = SHEET.format(name=html.escape(brand_name(d)), logo=logo, swatches="".join(sw),
                       font_display=fam(v.get("--brand-font-display")), font_body=fam(v.get("--brand-font-body")))
    (d / "brand-sheet.html").write_text(out, encoding="utf-8")
    print(f"wrote {d / 'brand-sheet.html'} ({len(sw)} colours{', logo' if logo else ', no logo file found'})")


def check_folder(d):
    errors, notes = [], []
    for f in FILES:
        if not (d / f).exists():
            errors.append(f"missing file: {f}")
    if errors:
        return errors, notes
    texts = {f: (d / f).read_text(encoding="utf-8") for f in FILES}

    for f, t in texts.items():
        left = sorted(set(SLOT_RE.findall(COMMENT_RE.sub("", t))))
        if left:
            errors.append(f"{f}: unfilled placeholders {', '.join(left)}")
        if f.endswith(".md") and "—" in body(t):
            errors.append(f"{f}: contains em dashes (use a period, comma or colon)")

    bible = sections(body(texts["brand-bible.md"]))
    for s in BIBLE_SECTIONS:
        if s not in bible:
            errors.append(f"brand-bible.md: missing section '{s}'")
        elif len(re.sub(r"\s+", " ", bible[s]).strip()) < MIN_SECTION_CHARS:
            errors.append(f"brand-bible.md: section '{s}' is empty or too thin")
    if not re.search(r"^#### Persona", body(texts["brand-bible.md"]), re.M):
        errors.append("brand-bible.md: needs at least one '#### Persona' under The customer")

    voice = sections(body(texts["voice-agent.md"]))
    for s in VOICE_SECTIONS:
        if s not in voice or len(voice[s].strip()) < MIN_SECTION_CHARS // 2:
            errors.append(f"voice-agent.md: section '{s}' missing or empty")

    offers = re.findall(r"^## Offer: (.+)$", body(texts["offers.md"]), re.M)
    if not offers:
        errors.append("offers.md: needs at least one '## Offer: <name>' section")

    v = css_vars(texts["root.css"])
    for k in REQUIRED_VARS:
        if not v.get(k):
            errors.append(f"root.css: {k} not set")
        elif "font" not in k and not HEX_RE.match(v[k]):
            errors.append(f"root.css: {k} = {v[k]} is not a hex colour")
    if all(HEX_RE.match(v.get(k, "")) for k in ("--brand-ink", "--brand-muted", "--brand-bg")):
        for k in ("--brand-ink", "--brand-muted"):
            r = contrast(v[k], v["--brand-bg"])
            if r < 4.5:
                notes.append(f"root.css: {k} on --brand-bg is {r:.1f}:1, below the 4.5:1 readability minimum")

    tbd = sum(t.count(TBD) for t in texts.values())
    if tbd:
        notes.append(f"{tbd} x '{TBD}' still open (list them in the bible's Open items)")
    if not (d / "brand-sheet.html").exists():
        notes.append("brand-sheet.html not generated yet (brand.py sheet)")
    return errors, notes


def cmd_check(a):
    cfg = load_config()
    d = brand_dir(cfg, a.business)
    errors, notes = check_folder(d)
    print(f"brand folder: {d}")
    for e in errors:
        print(f"FAIL  {e}")
    for n in notes:
        print(f"NOTE  {n}")
    if errors:
        sys.exit(1)
    print("PASS  brand set is complete")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("paths").set_defaults(fn=cmd_paths)
    s = sub.add_parser("scaffold"); s.add_argument("--name", required=True)
    s.add_argument("--business"); s.add_argument("--website"); s.set_defaults(fn=cmd_scaffold)
    for n, f in (("sheet", cmd_sheet), ("check", cmd_check)):
        s = sub.add_parser(n); s.add_argument("--business"); s.set_defaults(fn=f)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
