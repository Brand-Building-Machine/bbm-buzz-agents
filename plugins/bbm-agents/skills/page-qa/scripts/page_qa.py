#!/usr/bin/env python3
"""page_qa.py: pre-launch QA gate for a static landing page.

Usage:
  page_qa.py <page folder or index.html> [--mode draft|ship] [--out qa-report.md]
             [--json] [--no-render] [--chrome PATH]

Exit codes: 0 pass (warnings allowed), 1 fail, 2 usage error.

Static checks run in pure Python (html.parser). Rendered checks (overflow, tap
targets, screenshots) run only when Chrome, Chromium or Edge is found; set
PAGE_QA_CHROME to point at a browser binary if it lives somewhere unusual.
Stdlib only. Works on macOS, Windows and Linux.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
RANK = {PASS: 0, WARN: 1, FAIL: 2}
WIDTHS = (375, 768, 1024, 1440)
EM_DASH = "\u2014"

# --------------------------------------------------------------------------
# Placeholders
# --------------------------------------------------------------------------
# (label, regex, strong). Strong tokens are also searched inside scripts and
# local JS files; weak ones (TODO, lorem) only in visible text and attributes.
PLACEHOLDERS = [
    ("REPLACE_ME", re.compile(r"\b(?:REPLACE[_-]?ME|[Rr]eplace[_-][Mm]e)\b"), True),
    ("{{template slot}}", re.compile(r"\{\{[^{}\n]{0,80}\}\}"), True),
    ("lorem ipsum", re.compile(r"lorem\s+ipsum", re.I), False),
    ("TODO", re.compile(r"\bTODO\b"), False),
    ("TBD", re.compile(r"\bTBD\b"), False),
    ("[bracket placeholder]", re.compile(
        r"\[(?:client to provide|to be provided|phone(?: number)?|email|address|name|city|"
        r"company|business name|insert[^\]\n]{0,40}|your [^\]\n]{0,40}|placeholder)\]", re.I), False),
    ("000-000 number", re.compile(r"\(?\b000\)?[-. ]+000\b"), False),
    ("dummy tel: link", re.compile(r"tel:\+?1?[-. ]?0{7,}"), True),
    ("example domain", re.compile(r"\bexample\.(?:com|org|net)\b", re.I), True),
]

BOOKING_HOSTS = ("calendly.com", "cal.com", "acuityscheduling.com", "youcanbook.me",
                 "savvycal.com", "tidycal.com", "meetings.hubspot.com", "calendar.app.google",
                 "calendar.google.com", "squareup.com/appointments", "book.squareup.com",
                 "zcal.co", "setmore.com", "simplybook.me", "booksy.com", "vagaro.com",
                 "leadconnectorhq.com", "msgsndr.com", "opentable.com", "resy.com")

SKIP_TEXT_TAGS = {"script", "style", "template", "noscript"}
CONTROL_TAGS = {"input", "select", "textarea"}
NON_LABELLED_TYPES = {"hidden", "submit", "button", "reset", "image"}


def snippet(text, start, end, pad=30):
    a, b = max(0, start - pad), min(len(text), end + pad)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("..." if a else "") + s + ("..." if b < len(text) else "")


# --------------------------------------------------------------------------
# HTML parsing
# --------------------------------------------------------------------------
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.viewport = False
        self.title = None
        self.meta_description = None
        self.h1 = []
        self.imgs = []          # (attrs, line)
        self.forms = []         # {attrs, line, controls: [...]}
        self.labels_for = set()
        self.ids = set()
        self.anchors = []       # {href, line, text}
        self.refs = []          # (tag, attr, value, line)
        self.text = []          # (text, line)
        self.attr_text = []     # (tag, attr, value, line)
        self.scripts = []       # (text, line)
        self._skip = []
        self._in_title = False
        self._title_buf = []
        self._label_depth = 0
        self._form = None
        self._h1 = None
        self._a = None
        self._script = None

    # tags
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, selfclosing=True)

    def handle_starttag(self, tag, attrs, selfclosing=False):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        line = self.getpos()[0]
        if a.get("id"):
            self.ids.add(a["id"])
        for k in ("alt", "placeholder", "aria-label", "title", "value", "content", "href",
                  "src", "action", "data-endpoint"):
            if k in a and a[k] and not (tag == "meta" and k == "content" and
                                         a.get("name", "").lower() not in ("description",) and
                                         not a.get("property")):
                self.attr_text.append((tag, k, a[k], line))
        if tag == "html":
            self.lang = a.get("lang", "").strip() or None
        elif tag == "meta":
            name = a.get("name", "").lower()
            if name == "viewport" and a.get("content"):
                self.viewport = True
            elif name == "description":
                self.meta_description = a.get("content", "").strip()
        elif tag == "svg":
            self._svg_depth = getattr(self, "_svg_depth", 0) + 1
        elif tag == "title" and not getattr(self, "_svg_depth", 0) and self.title is None:
            self._in_title = True
            self._title_buf = []
        elif tag == "h1":
            self._h1 = []
            self.h1.append({"line": line, "text": ""})
        elif tag == "img":
            a = dict(a)
            if self._a is not None and self._a["attrs"].get("aria-label", "").strip():
                a["_in_labelled_control"] = "1"
            self.imgs.append((a, line))
        elif tag == "form":
            self._form = {"attrs": a, "line": line, "controls": []}
            self.forms.append(self._form)
        elif tag == "label":
            if a.get("for"):
                self.labels_for.add(a["for"])
            if not selfclosing:
                self._label_depth += 1
        elif tag == "a":
            self._a = {"href": a.get("href"), "line": line, "text": [], "attrs": a}
            self.anchors.append(self._a)
            if selfclosing:
                self._a = None
        elif tag == "script":
            if not selfclosing:
                self._script = {"text": [], "line": line}
        if tag in CONTROL_TAGS:
            ctl = {"tag": tag, "attrs": a, "line": line, "in_label": self._label_depth > 0}
            if self._form is not None:
                self._form["controls"].append(ctl)
            else:
                self.forms_orphans = getattr(self, "forms_orphans", [])
                self.forms_orphans.append(ctl)
        # local references
        for attr in ("src", "href", "poster", "data-src"):
            if a.get(attr):
                self.refs.append((tag, attr, a[attr], line))
        for attr in ("srcset", "data-srcset"):
            if a.get(attr):
                for part in a[attr].split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.refs.append((tag, attr, url, line))
        if tag in SKIP_TEXT_TAGS and not selfclosing:
            self._skip.append(tag)

    def handle_endtag(self, tag):
        if tag == "svg" and getattr(self, "_svg_depth", 0):
            self._svg_depth -= 1
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = re.sub(r"\s+", " ", "".join(self._title_buf)).strip()
        elif tag == "h1" and self._h1 is not None:
            self.h1[-1]["text"] = re.sub(r"\s+", " ", "".join(self._h1)).strip()
            self._h1 = None
        elif tag == "form":
            self._form = None
        elif tag == "label" and self._label_depth:
            self._label_depth -= 1
        elif tag == "a" and self._a is not None:
            self._a["text"] = re.sub(r"\s+", " ", "".join(self._a["text"])).strip()
            self._a = None
        elif tag == "script" and self._script is not None:
            self.scripts.append(("".join(self._script["text"]), self._script["line"]))
            self._script = None
        if self._skip and self._skip[-1] == tag:
            self._skip.pop()

    def handle_data(self, data):
        line = self.getpos()[0]
        if self._script is not None:
            self._script["text"].append(data)
            return
        if self._in_title:
            self._title_buf.append(data)
            self.text.append((data, line))
            return
        if self._skip:
            return
        if data.strip():
            self.text.append((data, line))
        if self._h1 is not None:
            self._h1.append(data)
        if self._a is not None:
            self._a["text"].append(data)


def parse_page(path):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    p = PageParser()
    p.feed(raw)
    p.close()
    return p, raw


def is_local_ref(value):
    v = value.strip()
    if not v or v.startswith(("#", "//", "data:", "blob:", "about:", "{{")):
        return False
    scheme = urlsplit(v).scheme.lower()
    if scheme and len(scheme) > 1:   # len 1 = a Windows drive letter
        return False
    return True


def resolve_local(base_dir, value, site_root):
    parts = urlsplit(value.strip())
    rel = unquote(parts.path)
    if not rel:
        return None
    if rel.startswith("/"):
        target = Path(site_root) / rel.lstrip("/")
    else:
        target = Path(base_dir) / rel
    if rel.endswith("/"):
        target = target / "index.html"
    return target


# --------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------
def check_placeholders(p, raw, mode, extra_files):
    found = []
    seen = set()

    def scan(text, where, line, strong_only=False):
        for label, rx, strong in PLACEHOLDERS:
            if strong_only and not strong:
                continue
            if label == "example domain" and where.endswith(" placeholder>"):
                continue    # name@example.com as an input hint is fine
            for m in rx.finditer(text):
                key = (label, where, line, m.group(0).lower())
                if key in seen:
                    continue
                seen.add(key)
                found.append({"token": label, "match": m.group(0), "where": where,
                              "line": line, "context": snippet(text, m.start(), m.end())})

    for text, line in p.text:
        scan(text, "text", line)
    for tag, attr, value, line in p.attr_text:
        scan(value, f"<{tag} {attr}>", line)
    for text, line in p.scripts:
        scan(text, "<script>", line, strong_only=True)
    for fpath in extra_files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, ln in enumerate(content.splitlines(), 1):
            scan(ln, fpath.name, i, strong_only=True)

    if not found:
        return {"status": PASS, "summary": "No placeholders found.", "items": found}
    status = FAIL if mode == "ship" else WARN
    tokens = sorted({f["token"] for f in found})
    return {"status": status,
            "summary": f"{len(found)} placeholder(s) left ({', '.join(tokens)})"
                       + ("; ship mode blocks these." if mode == "ship" else "; fine for a draft."),
            "items": found}


def tel_digits(href):
    num = unquote(href.split(":", 1)[1]).split("?")[0]
    return re.sub(r"\D", "", num)


def tel_is_placeholder(digits):
    core = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
    return bool(core) and (set(core) == {"0"} or core.startswith("000") or
                           core in ("1234567890", "5555555555") or len(set(core)) == 1)


def tel_plausible(digits):
    return 8 <= len(digits) <= 15 and not tel_is_placeholder(digits)


PLACEHOLDER_ACTION_RE = re.compile(r"REPLACE_ME|\{\{|TODO|TBD|YOUR[_-]?(ENDPOINT|FORM)", re.I)


def check_lead_capture(p):
    items, worst = [], PASS

    def add(status, msg, line=None):
        nonlocal worst
        items.append({"status": status, "message": msg, "line": line})
        if RANK[status] > RANK[worst]:
            worst = status

    labelled_ids = p.labels_for
    for i, form in enumerate(p.forms, 1):
        a = form["attrs"]
        name = f"form #{i} (line {form['line']})"
        action = a.get("action", "").strip()
        endpoint = a.get("data-endpoint", "").strip()
        method = a.get("method", "").strip().lower()
        if re.match(r"https?://", action, re.I):
            pass
        elif re.match(r"https?://", endpoint, re.I):
            add(PASS, f"{name}: posts via data-endpoint {endpoint}", form["line"])
        elif action and PLACEHOLDER_ACTION_RE.search(action):
            add(WARN, f"{name}: action '{action}' is a placeholder; set the real endpoint before launch "
                      "(blocks ship mode)", form["line"])
        elif action:
            add(FAIL, f"{name}: action '{action}' is not an absolute http(s) URL, so leads go nowhere",
                form["line"])
        else:
            add(FAIL, f"{name}: no action (and no data-endpoint), so leads go nowhere", form["line"])
        if method != "post" and not endpoint:
            add(FAIL, f"{name}: method is '{method or 'GET (default)'}', must be POST", form["line"])
        for ctl in form["controls"]:
            ca = ctl["attrs"]
            if "required" not in ca:
                continue
            if ctl["tag"] == "input" and ca.get("type", "text").lower() in NON_LABELLED_TYPES:
                continue
            ok = (ctl["in_label"] or (ca.get("id") and ca["id"] in labelled_ids)
                  or ca.get("aria-label", "").strip()
                  or any(t in p.ids for t in ca.get("aria-labelledby", "").split()))
            if not ok:
                ident = ca.get("name") or ca.get("id") or ctl["tag"]
                add(FAIL, f"{name}: required field '{ident}' has no label "
                          "(label for=, wrapping label, or aria-label)", ctl["line"])

    tels = [x for x in p.anchors if (x["href"] or "").strip().lower().startswith("tel:")]
    mailtos = [x for x in p.anchors if (x["href"] or "").strip().lower().startswith("mailto:")]
    booking = [x for x in p.anchors if any(h in (x["href"] or "").lower() for h in BOOKING_HOSTS)]
    if tels:
        good = [t for t in tels if tel_plausible(tel_digits(t["href"]))]
        placeholder = [t for t in tels if tel_is_placeholder(tel_digits(t["href"]))]
        bad = [t for t in tels if t not in good and t not in placeholder]
        if good:
            add(PASS, f"{len(good)} tel: link(s) with a plausible number, e.g. {good[0]['href']}")
        if placeholder and not good:
            add(WARN, f"{len(placeholder)} tel: link(s) use a dummy number ({placeholder[0]['href']}); "
                      "counted under placeholders", placeholder[0]["line"])
        for t in bad:
            add(FAIL, f"tel: link '{t['href']}' is not a plausible phone number", t["line"])
    elif p.forms or mailtos or booking:
        add(WARN, "No tel: link. Visitors who would rather call cannot tap to call.")

    if not (p.forms or tels or mailtos or booking):
        add(FAIL, "No way to convert: no form, no tel:, no mailto:, no booking link.")
    elif p.forms:
        add(PASS, f"{len(p.forms)} form(s) found")
    if mailtos:
        add(PASS, f"{len(mailtos)} mailto: link(s)")
    if booking:
        add(PASS, f"{len(booking)} booking link(s)")

    fails = [x for x in items if x["status"] == FAIL]
    warns = [x for x in items if x["status"] == WARN]
    summary = ("Lead capture wired." if worst == PASS else
               f"{len(fails)} problem(s)" if fails else f"{len(warns)} warning(s)")
    return {"status": worst, "summary": summary, "items": items}


def check_basics(p):
    items, worst = [], PASS

    def add(status, msg, line=None, context=None):
        nonlocal worst
        items.append({"status": status, "message": msg, "line": line, "context": context})
        if RANK[status] > RANK[worst]:
            worst = status

    add(PASS if p.lang else FAIL, f"<html lang=\"{p.lang}\">" if p.lang else "<html> has no lang attribute")
    add(PASS if p.viewport else FAIL, "meta viewport present" if p.viewport else "No <meta name=viewport>; the page will not scale on phones")
    add(PASS if p.title else FAIL, f"<title>: {p.title}" if p.title else "Missing or empty <title>")
    if p.meta_description:
        add(PASS, f"meta description ({len(p.meta_description)} chars)")
    else:
        add(WARN, "No meta description")
    n = len(p.h1)
    if n == 1:
        add(PASS, f"one <h1>: {p.h1[0]['text'][:80]}")
    else:
        add(FAIL, f"{n} <h1> elements (need exactly one)" +
            (": lines " + ", ".join(str(h["line"]) for h in p.h1) if n else ""))
    bad_imgs = 0
    for a, line in p.imgs:
        src = a.get("src", a.get("data-src", "?"))
        if "alt" not in a:
            add(FAIL, f"<img src=\"{src}\"> has no alt", line)
            bad_imgs += 1
        elif not a["alt"].strip():
            decorative = (a.get("role", "").lower() in ("presentation", "none")
                          or a.get("aria-hidden", "").lower() == "true"
                          or "data-decorative" in a
                          or "_in_labelled_control" in a
                          or "decor" in a.get("class", "").lower())
            if not decorative:
                add(FAIL, f"<img src=\"{src}\"> has empty alt but is not marked decorative "
                          "(add role=\"presentation\" or real alt text)", line)
                bad_imgs += 1
    if p.imgs and not bad_imgs:
        add(PASS, f"all {len(p.imgs)} <img> have usable alt")
    dashes = 0
    for text, line in p.text:
        for m in re.finditer(EM_DASH, text):
            dashes += 1
            add(FAIL, "em dash in visible text", line, snippet(text, m.start(), m.end()))
    for tag, attr, value, line in p.attr_text:
        if attr in ("alt", "placeholder", "aria-label", "title", "value") or (tag == "meta" and attr == "content"):
            for m in re.finditer(EM_DASH, value):
                dashes += 1
                add(FAIL, f"em dash in <{tag} {attr}>", line, snippet(value, m.start(), m.end()))
    if not dashes:
        add(PASS, "no em dashes in visible text")
    dead = [x for x in p.anchors if (x["href"] or "").strip() == "#"]
    for x in dead[:10]:
        add(WARN, f"link goes nowhere: href=\"#\" ({x['text'][:40] or 'no text'})", x["line"])
    fails = sum(1 for x in items if x["status"] == FAIL)
    warns = sum(1 for x in items if x["status"] == WARN)
    summary = "All basics in place." if worst == PASS else f"{fails} fail(s), {warns} warning(s)"
    return {"status": worst, "summary": summary, "items": items}


CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)|@import\s+['\"]([^'\"]+)['\"]", re.I)


def collect_local_files(p, page):
    """Return (resolved refs [(tag, attr, value, line, target)], local css files, local js files)."""
    base = page.parent
    out, css, js = [], [], []
    for tag, attr, value, line in p.refs:
        if tag == "a" and attr == "href" and not is_local_ref(value):
            continue
        if not is_local_ref(value):
            continue
        target = resolve_local(base, value, base)
        if target is None:
            continue
        out.append((tag, attr, value, line, target))
        low = target.name.lower()
        if low.endswith(".css") and target.is_file():
            css.append(target)
        elif low.endswith((".js", ".mjs")) and target.is_file():
            js.append(target)
    return out, css, js


def check_local_refs(p, page):
    refs, css_files, _ = collect_local_files(p, page)
    missing, checked = [], 0
    for tag, attr, value, line, target in refs:
        checked += 1
        if not target.exists():
            missing.append({"ref": value, "from": f"<{tag} {attr}>", "line": line})
    for css in css_files:
        try:
            content = css.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
        for m in CSS_URL.finditer(content):
            value = (m.group(1) or m.group(2) or "").strip()
            if not is_local_ref(value):
                continue
            target = resolve_local(css.parent, value, page.parent)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                line = content.count("\n", 0, m.start()) + 1
                missing.append({"ref": value, "from": css.name, "line": line})
    if missing:
        return {"status": FAIL, "summary": f"{len(missing)} of {checked} local reference(s) missing",
                "items": missing}
    return {"status": PASS, "summary": f"All {checked} local reference(s) resolve.", "items": []}


# --------------------------------------------------------------------------
# Rendered checks (headless Chrome)
# --------------------------------------------------------------------------
def find_chrome(explicit=None):
    cands = []
    if explicit:
        cands.append(explicit)
    env = os.environ.get("PAGE_QA_CHROME")
    if env:
        cands.append(env)
        if env.lower() in ("none", "off", "0"):
            return None
    home = Path.home()
    mac = ["Google Chrome.app/Contents/MacOS/Google Chrome",
           "Chromium.app/Contents/MacOS/Chromium",
           "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
           "Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
           "Brave Browser.app/Contents/MacOS/Brave Browser"]
    for root in ("/Applications", str(home / "Applications")):
        cands += [os.path.join(root, m) for m in mac]
    for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(var)
        if root:
            cands += [os.path.join(root, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(root, "Chromium", "Application", "chrome.exe"),
                      os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe")]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "chrome", "microsoft-edge", "microsoft-edge-stable", "msedge", "chrome.exe",
                 "msedge.exe"):
        w = shutil.which(name)
        if w:
            cands.append(w)
    cands += ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
              "/snap/bin/chromium", "/opt/google/chrome/chrome"]
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def run_chrome(chrome, args, url, workdir, timeout=45):
    """Run headless Chrome and return its stdout.

    Stdout goes to a file so lingering helper processes cannot hang a pipe. Headless
    Chrome uses its own throwaway profile; passing --user-data-dir makes some builds
    write their output and then never exit, so we don't. If Chrome overruns the
    timeout it is killed and whatever it already wrote is still returned.
    """
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--mute-audio", "--hide-scrollbars"] + args + [url]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")
    out_path = Path(workdir) / f"stdout-{len(os.listdir(workdir))}.txt"
    with open(out_path, "wb") as fh:
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
    return out_path.read_text(encoding="utf-8", errors="replace")


MEASURE_JS = r"""
function sel(el){
  var s = el.tagName.toLowerCase();
  if (el.id) s += '#' + el.id;
  if (typeof el.className === 'string' && el.className.trim())
    s += '.' + el.className.trim().split(/\s+/).slice(0,2).join('.');
  return s;
}
function clippedByAncestor(el, cw, win){
  var p = el.parentElement;
  while (p && p !== el.ownerDocument.documentElement && p !== el.ownerDocument.body){
    var cs = win.getComputedStyle(p);
    if (cs.overflowX !== 'visible' && p.getBoundingClientRect().right <= cw + 1) return true;
    p = p.parentElement;
  }
  return false;
}
function measure(frame, width, taps){
  var win = frame.contentWindow, d = frame.contentDocument, de = d.documentElement;
  var cw = de.clientWidth, sw = de.scrollWidth, res = {width: width, scrollWidth: sw, clientWidth: cw,
      overflow: sw > cw + 1, offenders: []};
  if (res.overflow){
    var all = d.body ? d.body.getElementsByTagName('*') : [], offs = [];
    for (var i = 0; i < all.length; i++){
      var r = all[i].getBoundingClientRect();
      if (r.width > 0 && r.right > cw + 1 && !clippedByAncestor(all[i], cw, win))
        offs.push({el: sel(all[i]), right: Math.round(r.right), width: Math.round(r.width)});
    }
    offs.sort(function(a,b){ return b.right - a.right; });
    res.offenders = offs.slice(0, 3);
  }
  if (taps){
    var q = d.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button], summary');
    var small = [], total = 0;
    for (var j = 0; j < q.length; j++){
      var el = q[j], cs = win.getComputedStyle(el), r2 = el.getBoundingClientRect();
      if (r2.width <= 2 || r2.height <= 2 || r2.right <= 0 || r2.bottom <= 0 || cs.visibility === 'hidden' || cs.display === 'none') continue;
      if (el.tagName === 'A' && cs.display === 'inline' && el.parentElement &&
          el.parentElement.textContent.trim().length > el.textContent.trim().length + 20) continue;
      total++;
      if (r2.width < 44 || r2.height < 44)
        small.push({el: sel(el), text: (el.textContent || el.value || el.getAttribute('aria-label') || '').trim().replace(/\s+/g,' ').slice(0,40),
                    w: Math.round(r2.width), h: Math.round(r2.height)});
    }
    res.taps = {total: total, small: small.length, examples: small.slice(0, 5)};
  }
  return res;
}
"""


def build_measure_harness(page_url, workdir):
    frames = "\n".join(
        f'<iframe data-w="{w}" src="{page_url}" style="width:{w}px;height:900px;border:0;display:block"></iframe>'
        for w in WIDTHS)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>pending</title></head>
<body style="margin:0">{frames}
<script>{MEASURE_JS}
var frames = document.querySelectorAll('iframe'), done = 0, out = [];
function finish(){{ document.title = 'QA:' + JSON.stringify(out); }}
Array.prototype.forEach.call(frames, function(f){{
  f.addEventListener('load', function(){{
    setTimeout(function(){{
      var w = parseInt(f.getAttribute('data-w'), 10);
      try {{ out.push(measure(f, w, w === 375)); }}
      catch (e) {{ out.push({{width: w, error: String(e && e.message || e)}}); }}
      done++; if (done === frames.length) finish();
    }}, 400);
  }});
}});
</script></body></html>"""
    path = Path(workdir) / "measure-harness.html"
    path.write_text(doc, encoding="utf-8")
    return path


def build_shot_harness(page_url, workdir):
    scale = 500 / 375
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>shot</title></head>
<body style="margin:0;overflow:hidden;background:#fff">
<iframe src="{page_url}" style="width:375px;height:2400px;border:0;display:block;transform:scale({scale:.6f});transform-origin:0 0"></iframe>
</body></html>"""
    path = Path(workdir) / "shot-harness.html"
    path.write_text(doc, encoding="utf-8")
    return path


def parse_title_payload(dom):
    if dom is None:
        return None
    m = re.search(r"<title>(.*?)</title>", dom, re.S)
    if not m:
        return None
    t = html.unescape(m.group(1)).strip()
    if not t.startswith("QA:"):
        return None
    try:
        return json.loads(t[3:])
    except ValueError:
        return None


def measure(chrome, page, workdir):
    """Return (list of per-width results, note) or (None, error message)."""
    harness = build_measure_harness(page.resolve().as_uri(), workdir)
    base = ["--dump-dom", "--virtual-time-budget=4000", "--window-size=1500,1000"]
    data = parse_title_payload(run_chrome(chrome, base, harness.as_uri(), workdir))
    note = "same-origin file:// iframe"
    if data is None or any("error" in r for r in data):
        data = parse_title_payload(run_chrome(chrome, base + ["--allow-file-access-from-files"],
                                              harness.as_uri(), workdir))
        note = "file:// iframe with --allow-file-access-from-files"
    if data is None:
        return None, "Chrome ran but the harness returned no measurements (timed out or blocked)"
    errs = [r for r in data if "error" in r]
    if errs:
        return None, "Chrome could not read the page inside the harness: " + errs[0]["error"]
    data.sort(key=lambda r: r["width"])
    return data, note


def screenshots(chrome, page, out_dir, workdir):
    shots = {}
    s1440 = Path(out_dir) / "shot-1440.png"
    run_chrome(chrome, ["--window-size=1440,3200", "--virtual-time-budget=4000",
                        f"--screenshot={s1440}"], page.resolve().as_uri(), workdir)
    if s1440.is_file():
        shots["1440"] = {"path": str(s1440), "how": "page loaded directly in a 1440x3200 window"}
    s375 = Path(out_dir) / "shot-375.png"
    harness = build_shot_harness(page.resolve().as_uri(), workdir)
    run_chrome(chrome, ["--window-size=500,3200", "--virtual-time-budget=4000",
                        "--allow-file-access-from-files", f"--screenshot={s375}"],
               harness.as_uri(), workdir)
    if s375.is_file():
        shots["375"] = {"path": str(s375),
                        "how": "harness: page laid out at 375 css px in an iframe, scaled 1.33x to fill "
                               "a 500x3200 window (shows the top 2400 css px)"}
    return shots


def rendered_checks(page, out_dir, chrome):
    skipped = {"status": WARN, "summary": "rendered checks skipped: no Chrome", "items": []}
    if not chrome:
        return {"overflow": dict(skipped), "tap_targets": dict(skipped),
                "screenshots": dict(skipped)}, None
    workdir = tempfile.mkdtemp(prefix="page-qa-")
    try:
        data, note = measure(chrome, page, workdir)
        if data is None:
            fail = {"status": WARN, "summary": f"rendered checks skipped: {note}", "items": []}
            res = {"overflow": dict(fail), "tap_targets": dict(fail)}
        else:
            over = [r for r in data if r["overflow"]]
            items = []
            for r in data:
                if r["overflow"]:
                    worst = r["offenders"][0] if r["offenders"] else None
                    msg = (f"{r['width']}px: content is {r['scrollWidth']}px wide, sideways scroll"
                           + (f"; widest offender {worst['el']} (right edge {worst['right']}px, "
                              f"{worst['width']}px wide)" if worst else ""))
                    items.append({"status": FAIL, "message": msg, "offenders": r["offenders"]})
                else:
                    items.append({"status": PASS, "message": f"{r['width']}px: no horizontal overflow"})
            res = {"overflow": {
                "status": FAIL if over else PASS,
                "summary": (f"horizontal overflow at {', '.join(str(r['width']) for r in over)}px"
                            if over else f"no horizontal overflow at {', '.join(map(str, WIDTHS))}px")
                           + f" ({note})",
                "items": items}}
            t = next((r.get("taps") for r in data if r["width"] == 375), None) or {}
            small = t.get("small", 0)
            res["tap_targets"] = {
                "status": WARN if small else PASS,
                "summary": (f"{small} of {t.get('total', 0)} tap targets at 375px are under 44x44 css px"
                            if small else f"all {t.get('total', 0)} tap targets at 375px are 44x44 or larger"),
                "items": [{"message": f"{e['el']} \"{e['text']}\" {e['w']}x{e['h']}"}
                          for e in t.get("examples", [])]}
        shots = screenshots(chrome, page, out_dir, workdir)
        res["screenshots"] = {
            "status": PASS if len(shots) == 2 else WARN,
            "summary": ("wrote " + ", ".join(Path(s["path"]).name for s in shots.values())
                        if shots else "Chrome did not write screenshots"),
            "items": [{"message": f"{Path(s['path']).name}: {s['how']}", "path": s["path"]}
                      for s in shots.values()]}
        return res, chrome
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --------------------------------------------------------------------------
# Orchestration + report
# --------------------------------------------------------------------------
CHECK_NAMES = [
    ("placeholders", "1. Placeholders"),
    ("lead_capture", "2. Lead capture"),
    ("basics", "3. Basics"),
    ("local_refs", "4. Local references"),
    ("overflow", "5. Horizontal overflow (rendered)"),
    ("tap_targets", "6. Tap targets at 375px (rendered)"),
    ("screenshots", "7. Screenshots (rendered)"),
]


def resolve_target(arg):
    t = Path(arg).expanduser()
    if t.is_dir():
        idx = t / "index.html"
        if not idx.is_file():
            raise ValueError(f"no index.html in folder {t}")
        return idx
    if t.is_file() and t.suffix.lower() in (".html", ".htm"):
        return t
    raise ValueError(f"not a page folder or .html file: {arg}")


def run_qa(target, mode="draft", out=None, render=True, chrome=None):
    page = resolve_target(target)
    out_path = Path(out).expanduser() if out else page.parent / "qa-report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    p, raw = parse_page(page)
    _, _, js_files = collect_local_files(p, page)
    checks = {
        "placeholders": check_placeholders(p, raw, mode, js_files),
        "lead_capture": check_lead_capture(p),
        "basics": check_basics(p),
        "local_refs": check_local_refs(p, page),
    }
    browser = find_chrome(chrome) if render else None
    rendered, used = rendered_checks(page, out_path.parent, browser)
    if not render:
        for v in rendered.values():
            v["summary"] = "rendered checks skipped: --no-render"
    checks.update(rendered)
    ordered = []
    for key, name in CHECK_NAMES:
        c = checks[key]
        ordered.append({"id": key, "name": name, **c})
    fails = [c for c in ordered if c["status"] == FAIL]
    warns = [c for c in ordered if c["status"] == WARN]
    if fails:
        verdict = f"FAIL ({mode} mode): {len(fails)} check(s) failed: " + ", ".join(c["name"] for c in fails)
    elif warns:
        verdict = f"PASS with {len(warns)} warning(s) ({mode} mode)"
    else:
        verdict = f"PASS ({mode} mode)"
    result = {"target": str(page), "mode": mode, "verdict": verdict,
              "passed": not fails, "exit_code": 1 if fails else 0,
              "browser": used, "report": str(out_path), "checks": ordered}
    out_path.write_text(render_markdown(result), encoding="utf-8")
    return result


def render_markdown(r):
    lines = [f"# Page QA: {Path(r['target']).parent.name}/{Path(r['target']).name}", "",
             f"**Verdict:** {r['verdict']}", "",
             f"- Page: `{r['target']}`", f"- Mode: {r['mode']}",
             f"- Browser: {'found' if r['browser'] else 'not used'}", "",
             "| Check | Result | Summary |", "|---|---|---|"]
    for c in r["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {c['summary'].replace('|', '/')} |")
    for c in r["checks"]:
        if not c["items"]:
            continue
        lines += ["", f"## {c['name']}: {c['status']}", ""]
        for it in c["items"][:40]:
            if c["id"] == "placeholders":
                lines.append(f"- `{it['match']}` ({it['token']}) in {it['where']}, line {it['line']}: {it['context']}")
            elif c["id"] == "local_refs":
                lines.append(f"- missing `{it['ref']}` (from {it['from']}, line {it['line']})")
            else:
                st = f"**{it['status']}** " if it.get("status") else ""
                ln = f" (line {it['line']})" if it.get("line") else ""
                ctx = f": {it['context']}" if it.get("context") else ""
                lines.append(f"- {st}{it['message']}{ln}{ctx}")
                for o in it.get("offenders", [])[1:]:
                    lines.append(f"  - also {o['el']} (right edge {o['right']}px)")
        if len(c["items"]) > 40:
            lines.append(f"- ...and {len(c['items']) - 40} more")
    lines += ["", f"Verdict: {r['verdict']}", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre-launch QA gate for a static landing page.")
    ap.add_argument("target", help="page folder (containing index.html) or an .html file")
    ap.add_argument("--mode", choices=("draft", "ship"), default="draft")
    ap.add_argument("--out", help="report path (default: qa-report.md next to the page); "
                                  "screenshots are written next to it")
    ap.add_argument("--json", action="store_true", help="print machine-readable results")
    ap.add_argument("--no-render", action="store_true", help="skip the headless-Chrome checks")
    ap.add_argument("--chrome", help="path to a Chrome/Chromium/Edge binary")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        r = run_qa(a.target, a.mode, a.out, render=not a.no_render, chrome=a.chrome)
    except ValueError as e:
        print(f"page_qa: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(r))
        print(f"Report written to {r['report']}")
    return r["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
