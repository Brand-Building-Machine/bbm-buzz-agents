#!/usr/bin/env python3
"""Social visuals engine: HTML slides -> PNG + PDF, images -> PDF, and AI image generation.
Stdlib only; macOS, Linux, Windows.

Rendering uses the owner's own installed Chrome, Edge, Chromium or Brave in headless mode (free).
Generation calls Fal or Higgsfield with the owner's OWN key and costs them money: the agent must get
the owner's yes before running `generate` without --dry-run.

  visuals.py browser                                  # which browser will render (exit 1 if none)
  visuals.py scaffold --kind carousel|single --out FILE [--size 1080x1350] [--brand-css root.css]
                                                      # starter HTML with the brand's CSS inlined (never overwrites)
  visuals.py render FILE.html --out DIR [--size 1080x1350] [--pdf NAME.pdf] [--no-png] [--no-pdf]
                                                      # each top-level <section class="slide"> -> slide-NN.png, all -> one PDF
  visuals.py pdf IMG [IMG ...] --out FILE.pdf [--size 1080x1350]
                                                      # stitch finished slide images into one PDF (image-route carousels)
  visuals.py inspect FILE [FILE ...]                  # pixel size + aspect of PNG/JPEG/WEBP files
  visuals.py keys [init]                              # which image keys are set (never prints them); init writes a blank keys file
  visuals.py generate --provider fal|higgsfield (--prompt TEXT | --prompts FILE.json) --out DIR
                      [--model ID] [--aspect 4:5] [--max 12] [--param key=value ...] [--dry-run]
                                                      # FILE.json = [{"name": "slide-01", "prompt": "..."}]

Exit codes: 0 ok, 1 failed, 2 config or usage problem.
"""
import argparse
import json
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
KEYS_FILE = Path(os.environ.get("BBM_AGENTS_ENV") or (Path.home() / ".bbm-agents.env")).expanduser()
DEFAULT_SIZE = "1080x1350"
DEFAULT_MAX = 12
RENDER_TIMEOUT = 90

PROVIDERS = {
    "fal": {"default_model": "fal-ai/nano-banana-pro", "keys": ["FAL_KEY"],
            "models_page": "https://fal.ai/models"},
    "higgsfield": {"default_model": "ideogram/v4.0", "keys": ["HF_API_KEY_ID", "HF_API_KEY_SECRET"],
                   "models_page": "https://docs.higgsfield.ai/docs/models"},
}
HF_BASE = "https://api.higgsfield.ai/"
HF_TERMINAL = {"completed", "failed", "nsfw", "canceled"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def parse_size(s):
    m = re.fullmatch(r"\s*(\d{2,5})\s*[xX]\s*(\d{2,5})\s*", s or "")
    if not m:
        die(f"Bad --size {s!r}. Use WIDTHxHEIGHT, e.g. 1080x1350.")
    return int(m.group(1)), int(m.group(2))


# ---------- browser ----------

def browser_candidates():
    env = os.environ.get("BBM_BROWSER")
    if env:
        return [Path(env)]
    c = []
    if sys.platform == "darwin":
        for app, exe in [("Google Chrome", "Google Chrome"), ("Microsoft Edge", "Microsoft Edge"),
                         ("Chromium", "Chromium"), ("Brave Browser", "Brave Browser")]:
            for root in (Path("/Applications"), Path.home() / "Applications"):
                c.append(root / f"{app}.app" / "Contents" / "MacOS" / exe)
    elif os.name == "nt":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        for r in filter(None, roots):
            c += [Path(r) / "Google" / "Chrome" / "Application" / "chrome.exe",
                  Path(r) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                  Path(r) / "Chromium" / "Application" / "chrome.exe",
                  Path(r) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "microsoft-edge-stable", "brave-browser", "chrome", "msedge"):
        w = shutil.which(name)
        if w:
            c.append(Path(w))
    return c


def find_browser(required=True):
    for p in browser_candidates():
        if p.exists():
            return p
    if required:
        die("No Chrome, Edge, Chromium or Brave found to render with. Install Google Chrome "
            "(or set BBM_BROWSER to the browser's full path), or use the image-generation route.", 1)
    return None


def _stable(path, wait=0.6):
    if not path.exists() or path.stat().st_size == 0:
        return False
    size = path.stat().st_size
    time.sleep(wait)
    return path.exists() and path.stat().st_size == size


def run_browser(args, out_file, timeout=RENDER_TIMEOUT):
    """Run headless Chrome/Edge until out_file exists and stops growing, then stop it.
    Some builds (seen on macOS) never exit on their own after --screenshot / --print-to-pdf."""
    browser = find_browser()
    out_file = Path(out_file)
    if out_file.exists():
        out_file.unlink()
    profile = tempfile.mkdtemp(prefix="bbm-render-")
    cmd = [str(browser), "--headless", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions", "--mute-audio",
           f"--user-data-dir={profile}", *args]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            if _stable(out_file):
                return out_file
            if proc.poll() is not None:
                if _stable(out_file, wait=0.2):
                    return out_file
                die(f"The browser exited without writing {out_file.name} (exit {proc.returncode}).", 1)
            time.sleep(0.3)
        die(f"The browser took longer than {timeout}s to write {out_file.name}.", 1)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


# ---------- HTML slides ----------

SECTION_TAG = re.compile(r"<(/?)section\b([^>]*)>", re.I)
CLASS_ATTR = re.compile(r"""class\s*=\s*(["'])(.*?)\1""", re.I | re.S)


MASKED = re.compile(r"<!--.*?-->|<(style|script|template|textarea)\b.*?</\1\s*>", re.I | re.S)


def _mask(html):
    """Blank out comments, <style> and <script> (same length) so tags mentioned inside them are ignored."""
    return MASKED.sub(lambda m: " " * len(m.group(0)), html)


def split_slides(html):
    """Return (head_inner, [slide_html, ...]) for top-level <section class="... slide ...">."""
    m = re.search(r"<head\b[^>]*>(.*?)</head>", html, re.I | re.S)
    head = m.group(1) if m else ""
    slides, depth, start, is_slide = [], 0, None, False
    for t in SECTION_TAG.finditer(_mask(html)):
        closing = t.group(1) == "/"
        if not closing:
            if depth == 0:
                cls = CLASS_ATTR.search(t.group(2))
                is_slide = bool(cls and "slide" in cls.group(2).split())
                start = t.start()
            depth += 1
        else:
            depth -= 1
            if depth < 0:
                die("Unbalanced </section> in the slides file.")
            if depth == 0 and is_slide:
                slides.append(html[start:t.end()])
    if depth != 0:
        die("A <section> is never closed in the slides file.")
    return head, slides


def page_doc(head, body, w, h, paged):
    css = (f"@page{{size:{w}px {h}px;margin:0}}html,body{{margin:0!important;padding:0!important;"
           f"background:transparent}}.slide{{width:{w}px!important;height:{h}px!important;"
           f"box-sizing:border-box;overflow:hidden;position:relative}}")
    if paged:
        css += (".slide{break-after:page;page-break-after:always}"
                ".slide:last-of-type{break-after:auto;page-break-after:auto}")
    return (f"<!doctype html><html><head>{head}<style>{css}</style></head>"
            f"<body>{body}</body></html>")


def render_html(src, out_dir, size, pdf_name, png=True, pdf=True):
    src = Path(src).resolve()
    if not src.exists():
        die(f"No such file: {src}")
    w, h = parse_size(size)
    head, slides = split_slides(src.read_text(encoding="utf-8"))
    if not slides:
        die('No slides found. Each slide must be a top-level <section class="slide">.')
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    # Temp pages sit next to the source so relative image and font paths still resolve.
    tmp = []
    try:
        if png:
            for i, s in enumerate(slides, 1):
                page = src.parent / f".render-{src.stem}-{i:02d}.html"
                page.write_text(page_doc(head, s, w, h, paged=False), encoding="utf-8")
                tmp.append(page)
                out = out_dir / f"slide-{i:02d}.png"
                run_browser([f"--window-size={w},{h}", "--virtual-time-budget=4000",
                             f"--screenshot={out}", page.as_uri()], out)
                made.append(out)
        if pdf:
            page = src.parent / f".render-{src.stem}-all.html"
            page.write_text(page_doc(head, "".join(slides), w, h, paged=True), encoding="utf-8")
            tmp.append(page)
            out = out_dir / (pdf_name or f"{src.stem}.pdf")
            run_browser(["--no-pdf-header-footer", "--virtual-time-budget=4000",
                         f"--print-to-pdf={out}", page.as_uri()], out)
            made.append(out)
    finally:
        for p in tmp:
            try:
                p.unlink()
            except OSError:
                pass
    return slides, made


def images_to_pdf(images, out, size):
    w, h = parse_size(size)
    paths = [Path(i).resolve() for i in images]
    for p in paths:
        if not p.exists():
            die(f"No such image: {p}")
    body = "".join(f'<section class="slide"><img src="{p.as_uri()}" style="width:100%;height:100%;'
                   f'object-fit:cover;display:block"></section>' for p in paths)
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    page = out.parent / f".render-{out.stem}-images.html"
    page.write_text(page_doc("<meta charset='utf-8'>", body, w, h, paged=True), encoding="utf-8")
    try:
        run_browser(["--no-pdf-header-footer", "--allow-file-access-from-files",
                     "--virtual-time-budget=4000", f"--print-to-pdf={out}", page.as_uri()], out)
    finally:
        page.unlink(missing_ok=True)
    return out


def scaffold(kind, out, size, brand_css):
    out = Path(out)
    if out.exists():
        die(f"{out} already exists; not overwriting.", 1)
    tpl = TEMPLATES / ("carousel.html" if kind == "carousel" else "single.html")
    w, h = parse_size(size)
    css = ""
    if brand_css:
        bc = Path(brand_css)
        if not bc.exists():
            die(f"No brand CSS at {bc}. Run brand-bible first, or scaffold without --brand-css.", 1)
        css = bc.read_text(encoding="utf-8")
    text = (tpl.read_text(encoding="utf-8").replace("/*BRAND_CSS*/", css)
            .replace("{{W}}", str(w)).replace("{{H}}", str(h)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


# ---------- image files ----------

def image_size(path):
    b = Path(path).read_bytes()[:64 * 1024]
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", b[16:24])
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        if b[12:16] == b"VP8X":
            return (int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1)
        if b[12:16] == b"VP8 ":
            return (struct.unpack("<H", b[26:28])[0] & 0x3FFF, struct.unpack("<H", b[28:30])[0] & 0x3FFF)
        if b[12:16] == b"VP8L":
            bits = int.from_bytes(b[21:25], "little")
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if b[:2] == b"\xff\xd8":
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            marker = b[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


def ext_for(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".img"


# ---------- keys ----------

KEYS_TEMPLATE = """# Image-generation keys for the bbm-agents social skills. This file stays on this computer.
# Never put it in a git repo, a shared folder or a chat message.
# Fal: https://fal.ai/dashboard/keys
FAL_KEY=
# Higgsfield: https://console.higgsfield.ai (API keys give a key ID and a secret)
HF_API_KEY_ID=
HF_API_KEY_SECRET=
"""


def read_keys_file():
    vals = {}
    if KEYS_FILE.exists():
        for line in KEYS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:
                vals[k.strip()] = v
    return vals


def get_key(name):
    """(value, source) from the environment first, then the keys file. Never logged."""
    if os.environ.get(name):
        return os.environ[name], "environment"
    v = read_keys_file().get(name)
    return (v, str(KEYS_FILE)) if v else (None, None)


def provider_auth(provider):
    if provider == "fal":
        k, _ = get_key("FAL_KEY")
        return f"Key {k}" if k else None
    kid, _ = get_key("HF_API_KEY_ID")
    sec, _ = get_key("HF_API_KEY_SECRET")
    if kid and sec:
        return f"Key {kid}:{sec}"
    combo, _ = get_key("HF_KEY")  # the Higgsfield SDK's "id:secret" form
    return f"Key {combo}" if combo and ":" in combo else None


def keys_status():
    rows = []
    for prov, spec in PROVIDERS.items():
        names = spec["keys"] + (["HF_KEY"] if prov == "higgsfield" else [])
        found = {n: get_key(n)[1] for n in names}
        rows.append({"provider": prov, "ready": provider_auth(prov) is not None,
                     "found": {n: s for n, s in found.items() if s}})
    return rows


# ---------- generation ----------

def http_json(url, auth, body=None, timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Authorization": auth, "Content-Type": "application/json",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:500]
        hint = {401: " (the key is wrong or expired)", 402: " (out of credit)",
                403: " (this key can't use that model)", 404: " (unknown model id)",
                422: " (the model rejected a parameter)", 429: " (rate limited; wait and retry)"}
        raise RuntimeError(f"HTTP {e.code}{hint.get(e.code, '')}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason}")


def first_image_url(payload):
    imgs = payload.get("images") or (payload.get("data") or {}).get("images") or []
    if not imgs and payload.get("image"):
        imgs = [payload["image"]]
    if not imgs:
        return None
    first = imgs[0]
    return first.get("url") if isinstance(first, dict) else first


def fal_generate(model, body, auth):
    payload = http_json(f"https://fal.run/{model}", auth, body)
    url = first_image_url(payload)
    if not url:
        raise RuntimeError(f"Fal returned no image: {json.dumps(payload)[:300]}")
    return url, payload.get("request_id")


def higgsfield_generate(model, body, auth, timeout=300, sleep=time.sleep):
    sub = http_json(HF_BASE + model, auth, body)
    rid = sub.get("request_id")
    status_url = sub.get("status_url") or (f"{HF_BASE}requests/{rid}/status" if rid else None)
    if not status_url:
        raise RuntimeError(f"Higgsfield did not accept the request: {json.dumps(sub)[:300]}")
    res, delay, waited = sub, 2.0, 0.0
    while res.get("status") not in HF_TERMINAL:
        if waited > timeout:
            raise RuntimeError(f"Higgsfield request {rid} still running after {timeout}s")
        sleep(delay + random.uniform(0, 0.5))
        waited += delay
        delay = min(delay * 1.5, 10.0)
        try:
            res = http_json(status_url, auth)
        except RuntimeError as e:
            if "HTTP 5" in str(e) or "network error" in str(e):
                continue
            raise
    if res["status"] != "completed":
        raise RuntimeError(f"Higgsfield request {rid} ended '{res['status']}': {res.get('error', '')}")
    url = first_image_url(res)
    if not url:
        raise RuntimeError(f"Higgsfield completed with no image: {json.dumps(res)[:300]}")
    return url, rid


def build_body(provider, model, prompt, aspect, params):
    body = {"prompt": prompt, "aspect_ratio": aspect}
    if provider == "fal":
        body.update({"num_images": 1, "output_format": "png"})
    elif model.startswith("recraft/"):
        body["resolution"] = "1k"
    body.update(params)
    return body


def parse_params(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            die(f"Bad --param {it!r}; use key=value.")
        k, v = it.split("=", 1)
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def load_jobs(a):
    if a.prompt:
        return [{"name": "image-01", "prompt": a.prompt}]
    p = Path(a.prompts)
    if not p.exists():
        die(f"No such prompts file: {p}")
    try:
        jobs = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"{p} is not valid JSON: {e}")
    if not isinstance(jobs, list) or not jobs:
        die("Prompts file must be a non-empty JSON list of {\"name\", \"prompt\"}.")
    seen = set()
    for i, j in enumerate(jobs, 1):
        if not isinstance(j, dict) or not str(j.get("prompt", "")).strip():
            die(f"Prompt #{i} has no prompt text.")
        name = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(j.get("name") or f"image-{i:02d}")).strip("-")
        if name in seen:
            die(f"Duplicate name {name!r} in prompts file.")
        seen.add(name)
        j["name"] = name
    return jobs


def download(url, dest_base):
    with urllib.request.urlopen(url, timeout=180) as r:
        data = r.read()
    dest = Path(str(dest_base) + ext_for(data))
    dest.write_bytes(data)
    return dest


def cmd_generate(a):
    spec = PROVIDERS[a.provider]
    model = a.model or spec["default_model"]
    jobs = load_jobs(a)
    if len(jobs) > a.max:
        die(f"{len(jobs)} images requested but the cap is {a.max}. Confirm the count with the owner, "
            f"then pass --max {len(jobs)}.", 1)
    params = parse_params(a.param)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "generation.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    requests = [{"name": j["name"], "body": build_body(a.provider, model, j["prompt"],
                                                       j.get("aspect") or a.aspect, params)} for j in jobs]
    if a.dry_run:
        print(json.dumps({"provider": a.provider, "model": model, "count": len(jobs),
                          "endpoint": ("https://fal.run/" if a.provider == "fal" else HF_BASE) + model,
                          "requests": requests, "price_check": spec["models_page"]}, indent=2))
        return 0
    auth = provider_auth(a.provider)
    if not auth:
        die(f"No {a.provider} key found. Run `visuals.py keys init`, then the owner pastes their own key "
            f"into {KEYS_FILE} (or sets {' + '.join(spec['keys'])} in their environment).", 2)
    failed = 0
    for r in requests:
        rec = {"name": r["name"], "provider": a.provider, "model": model, "prompt": r["body"]["prompt"],
               "aspect": r["body"].get("aspect_ratio"), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            fn = fal_generate if a.provider == "fal" else higgsfield_generate
            url, rid = fn(model, r["body"], auth)
            f = download(url, out_dir / r["name"])
            size = image_size(f)
            rec.update({"status": "ok", "file": f.name, "request_id": rid,
                        "pixels": f"{size[0]}x{size[1]}" if size else "unknown"})
            print(f"ok  {f.name}  {rec['pixels']}")
        except (RuntimeError, OSError) as e:
            failed += 1
            rec.update({"status": "failed", "error": str(e)[:500]})
            print(f"FAILED  {r['name']}: {e}", file=sys.stderr)
        manifest.append(rec)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(requests) - failed} of {len(requests)} generated with {a.provider} {model}. "
          f"Log: {manifest_path}")
    return 1 if failed else 0


# ---------- CLI ----------

def expand_globs(items):
    """Windows shells don't expand *.png; do it here, sorted, so slide order is stable."""
    import glob
    out = []
    for it in items:
        if any(ch in it for ch in "*?["):
            hits = sorted(glob.glob(it))
            if not hits:
                die(f"No files match {it}")
            out += hits
        else:
            out.append(it)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("browser")
    s = sub.add_parser("scaffold")
    s.add_argument("--kind", choices=["carousel", "single"], required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--size", default=DEFAULT_SIZE)
    s.add_argument("--brand-css")
    r = sub.add_parser("render")
    r.add_argument("file")
    r.add_argument("--out", required=True)
    r.add_argument("--size", default=DEFAULT_SIZE)
    r.add_argument("--pdf")
    r.add_argument("--no-png", action="store_true")
    r.add_argument("--no-pdf", action="store_true")
    p = sub.add_parser("pdf")
    p.add_argument("images", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--size", default=DEFAULT_SIZE)
    i = sub.add_parser("inspect")
    i.add_argument("files", nargs="+")
    k = sub.add_parser("keys")
    k.add_argument("action", nargs="?", choices=["status", "init"], default="status")
    g = sub.add_parser("generate")
    g.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    src = g.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt")
    src.add_argument("--prompts")
    g.add_argument("--out", required=True)
    g.add_argument("--model")
    g.add_argument("--aspect", default="4:5")
    g.add_argument("--max", type=int, default=DEFAULT_MAX)
    g.add_argument("--param", action="append")
    g.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    for attr in ("images", "files"):
        if hasattr(a, attr):
            setattr(a, attr, expand_globs(getattr(a, attr)))

    if a.cmd == "browser":
        b = find_browser(required=False)
        if not b:
            print("No browser found. Install Google Chrome, or set BBM_BROWSER to a Chrome/Edge path.")
            return 1
        print(b)
        return 0
    if a.cmd == "scaffold":
        print(scaffold(a.kind, a.out, a.size, a.brand_css))
        return 0
    if a.cmd == "render":
        if a.no_png and a.no_pdf:
            die("Nothing to do: --no-png and --no-pdf together.")
        slides, made = render_html(a.file, a.out, a.size, a.pdf, png=not a.no_png, pdf=not a.no_pdf)
        print(f"{len(slides)} slide(s) rendered at {a.size}:")
        for m in made:
            print(f"  {m}")
        return 0
    if a.cmd == "pdf":
        print(images_to_pdf(a.images, a.out, a.size))
        return 0
    if a.cmd == "inspect":
        bad = 0
        for f in a.files:
            if not Path(f).exists():
                print(f"{f}: missing")
                bad += 1
                continue
            sz = image_size(f)
            print(f"{f}: {sz[0]}x{sz[1]} (aspect {sz[0] / sz[1]:.3f})" if sz else f"{f}: unknown format")
        return 1 if bad else 0
    if a.cmd == "keys":
        if a.action == "init":
            if KEYS_FILE.exists():
                print(f"{KEYS_FILE} already exists; left as is.")
            else:
                KEYS_FILE.write_text(KEYS_TEMPLATE, encoding="utf-8")
                try:
                    os.chmod(KEYS_FILE, 0o600)
                except OSError:
                    pass
                print(f"Created {KEYS_FILE}. The owner opens it and pastes their own key(s).")
            return 0
        for row in keys_status():
            where = ", ".join(f"{n} ({s})" for n, s in row["found"].items()) or "no key found"
            print(f"{row['provider']:11} {'ready' if row['ready'] else 'not set':8} {where}")
        print(f"Keys file: {KEYS_FILE}")
        return 0
    if a.cmd == "generate":
        return cmd_generate(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())
