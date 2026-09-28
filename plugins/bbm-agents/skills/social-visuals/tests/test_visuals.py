"""Offline tests for visuals.py. Run from outside the skill dir:
    python3 -m pytest <abs path>/tests -q -p no:cacheprovider
The render test runs only when a Chrome/Edge/Chromium is installed; nothing here calls Fal or Higgsfield.
"""
import io
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import visuals  # noqa: E402

VIS = SCRIPTS / "visuals.py"


def png_bytes(w, h):
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * w for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def run(*args, env=None, cwd=None):
    return subprocess.run([sys.executable, str(VIS), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, encoding="utf-8", cwd=cwd)


# ---------- slide splitting ----------

def test_split_ignores_comments_styles_and_non_slides():
    html = """<html><head><style>/* a <section class="slide"> in a comment */ .x{}</style></head><body>
    <!-- <section class="slide">commented out</section> -->
    <section class="intro">not a slide</section>
    <section class="slide cover"><h1>One</h1><section class="inner">nested ok</section></section>
    <section class="slide"><h2>Two</h2></section>
    <script>var s = '<section class="slide">';</script>
    </body></html>"""
    head, slides = visuals.split_slides(html)
    assert "<style>" in head
    assert len(slides) == 2
    assert "One" in slides[0] and "nested ok" in slides[0]
    assert "Two" in slides[1]


def test_split_unbalanced_fails():
    with pytest.raises(SystemExit):
        visuals.split_slides('<section class="slide"><p>open</p>')


def test_page_doc_sets_page_size_and_breaks():
    doc = visuals.page_doc("<meta charset='utf-8'>", "<section class='slide'></section>", 1080, 1350, True)
    assert "@page{size:1080px 1350px" in doc
    assert "break-after:page" in doc
    assert "break-after" not in visuals.page_doc("", "", 1080, 1350, False)


def test_parse_size():
    assert visuals.parse_size("1080x1350") == (1080, 1350)
    with pytest.raises(SystemExit):
        visuals.parse_size("big")


# ---------- scaffold ----------

def test_scaffold_inlines_brand_css_and_never_overwrites(tmp_path):
    css = tmp_path / "root.css"
    css.write_text(":root{--brand-primary:#123456}", encoding="utf-8")
    out = tmp_path / "w" / "slides.html"
    r = run("scaffold", "--kind", "carousel", "--out", out, "--size", "1080x1080", "--brand-css", css)
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert "#123456" in text and "--s-h: 1080px" in text and "{{" not in text
    _, slides = visuals.split_slides(text)
    assert len(slides) == 5
    assert run("scaffold", "--kind", "carousel", "--out", out).returncode == 1
    single = tmp_path / "single.html"
    assert run("scaffold", "--kind", "single", "--out", single).returncode == 0
    assert len(visuals.split_slides(single.read_text(encoding="utf-8"))[1]) == 1


def test_scaffold_missing_brand_css(tmp_path):
    r = run("scaffold", "--kind", "single", "--out", tmp_path / "a.html", "--brand-css", tmp_path / "no.css")
    assert r.returncode == 1 and "brand-bible" in r.stderr


# ---------- images ----------

def test_image_size_png_jpeg_and_ext(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(png_bytes(8, 10))
    assert visuals.image_size(p) == (8, 10)
    assert visuals.ext_for(p.read_bytes()) == ".png"
    jpg = (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
           + b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 1350, 1080) + b"\x00" * 10)
    j = tmp_path / "b.jpg"
    j.write_bytes(jpg)
    assert visuals.image_size(j) == (1080, 1350)
    assert visuals.ext_for(jpg) == ".jpg"


def test_inspect_expands_globs(tmp_path):
    for n in ("slide-02.png", "slide-01.png"):
        (tmp_path / n).write_bytes(png_bytes(4, 5))
    r = run("inspect", str(tmp_path / "slide-*.png"))
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert lines[0].startswith(str(tmp_path / "slide-01.png")) and "4x5" in lines[0]
    assert run("inspect", str(tmp_path / "nothing-*.png")).returncode == 2


# ---------- keys ----------

def test_keys_file_and_env(tmp_path, monkeypatch):
    kf = tmp_path / "k.env"
    monkeypatch.setattr(visuals, "KEYS_FILE", kf)
    monkeypatch.delenv("FAL_KEY", raising=False)
    for k in ("HF_API_KEY_ID", "HF_API_KEY_SECRET", "HF_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert visuals.provider_auth("fal") is None
    kf.write_text('# c\nFAL_KEY="abc123"\nexport HF_API_KEY_ID=id1\nHF_API_KEY_SECRET=\n', encoding="utf-8")
    assert visuals.provider_auth("fal") == "Key abc123"
    assert visuals.provider_auth("higgsfield") is None  # secret is blank
    monkeypatch.setenv("HF_API_KEY_SECRET", "sec")
    assert visuals.provider_auth("higgsfield") == "Key id1:sec"
    monkeypatch.setenv("FAL_KEY", "fromenv")
    assert visuals.provider_auth("fal") == "Key fromenv"


def test_keys_cli_never_prints_values(tmp_path):
    kf = tmp_path / "k.env"
    env = {"BBM_AGENTS_ENV": str(kf), "FAL_KEY": "", "HF_API_KEY_ID": "", "HF_API_KEY_SECRET": "", "HF_KEY": ""}
    assert run("keys", "init", env=env).returncode == 0
    assert "FAL_KEY=" in kf.read_text(encoding="utf-8")
    kf.write_text("FAL_KEY=supersecretvalue\n", encoding="utf-8")
    r = run("keys", env=env)
    assert "supersecretvalue" not in r.stdout + r.stderr
    assert "fal" in r.stdout and "ready" in r.stdout
    r = run("keys", "init", env=env)
    assert "already exists" in r.stdout
    assert kf.read_text(encoding="utf-8") == "FAL_KEY=supersecretvalue\n"


# ---------- generation (no network) ----------

def write_prompts(tmp, n):
    p = tmp / "prompts.json"
    p.write_text(json.dumps([{"name": f"slide {i + 1:02d}", "prompt": f"p{i}"} for i in range(n)]),
                 encoding="utf-8")
    return p


def test_generate_dry_run_builds_requests(tmp_path):
    p = write_prompts(tmp_path, 2)
    r = run("generate", "--provider", "higgsfield", "--model", "recraft/v4.1/text-to-image",
            "--prompts", p, "--out", tmp_path / "art", "--dry-run", "--param", "output_format=png")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["endpoint"] == "https://api.higgsfield.ai/recraft/v4.1/text-to-image"
    body = d["requests"][0]["body"]
    assert body == {"prompt": "p0", "aspect_ratio": "4:5", "resolution": "1k", "output_format": "png"}
    assert d["requests"][0]["name"] == "slide-01"
    r = run("generate", "--provider", "fal", "--prompt", "x", "--out", tmp_path / "a", "--dry-run")
    body = json.loads(r.stdout)["requests"][0]["body"]
    assert body["num_images"] == 1 and json.loads(r.stdout)["model"] == "fal-ai/nano-banana-pro"


def test_generate_cap_and_missing_key(tmp_path):
    p = write_prompts(tmp_path, 13)
    r = run("generate", "--provider", "fal", "--prompts", p, "--out", tmp_path / "a", "--dry-run")
    assert r.returncode == 1 and "--max 13" in r.stderr
    env = {"BBM_AGENTS_ENV": str(tmp_path / "none.env"), "FAL_KEY": ""}
    r = run("generate", "--provider", "fal", "--prompt", "x", "--out", tmp_path / "a", env=env)
    assert r.returncode == 2 and "keys init" in r.stderr


def test_bad_prompts_file(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps([{"name": "a", "prompt": " "}]), encoding="utf-8")
    assert run("generate", "--provider", "fal", "--prompts", p, "--out", tmp_path, "--dry-run").returncode == 2
    p.write_text(json.dumps([{"name": "a", "prompt": "x"}, {"name": "a", "prompt": "y"}]), encoding="utf-8")
    r = run("generate", "--provider", "fal", "--prompts", p, "--out", tmp_path, "--dry-run")
    assert r.returncode == 2 and "Duplicate" in r.stderr


def test_higgsfield_polls_until_complete(monkeypatch):
    calls = []
    replies = [{"status": "queued", "request_id": "r1", "status_url": "https://api.higgsfield.ai/requests/r1/status"},
               {"status": "in_progress"},
               RuntimeError("HTTP 503: busy"),
               {"status": "completed", "images": [{"url": "https://cdn/x.png"}]}]

    def fake(url, auth, body=None, timeout=300):
        calls.append((url, body))
        r = replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(visuals, "http_json", fake)
    url, rid = visuals.higgsfield_generate("ideogram/v4.0", {"prompt": "p"}, "Key a:b", sleep=lambda s: None)
    assert url == "https://cdn/x.png" and rid == "r1"
    assert calls[0] == ("https://api.higgsfield.ai/ideogram/v4.0", {"prompt": "p"})
    assert all(c[0].endswith("/status") for c in calls[1:])


@pytest.mark.parametrize("final", ["failed", "nsfw", "canceled"])
def test_higgsfield_terminal_failures(monkeypatch, final):
    replies = [{"status": "queued", "request_id": "r", "status_url": "u"}, {"status": final, "error": "why"}]
    monkeypatch.setattr(visuals, "http_json", lambda *a, **k: replies.pop(0))
    with pytest.raises(RuntimeError, match=final):
        visuals.higgsfield_generate("m", {}, "Key a:b", sleep=lambda s: None)


def test_fal_reads_image_url(monkeypatch):
    monkeypatch.setattr(visuals, "http_json", lambda url, auth, body=None, timeout=300:
                        {"images": [{"url": "https://fal/x.png"}], "request_id": "q"})
    assert visuals.fal_generate("fal-ai/nano-banana-pro", {"prompt": "p"}, "Key k") == ("https://fal/x.png", "q")
    monkeypatch.setattr(visuals, "http_json", lambda *a, **k: {"images": []})
    with pytest.raises(RuntimeError):
        visuals.fal_generate("m", {}, "Key k")


def test_generate_logs_failures_and_successes(tmp_path, monkeypatch):
    monkeypatch.setattr(visuals, "provider_auth", lambda p: "Key k")
    results = iter([("https://fal/ok.png", "r1"), RuntimeError("HTTP 422: bad")])

    def fake_gen(model, body, auth):
        r = next(results)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(visuals, "fal_generate", fake_gen)
    def fake_download(url, base):
        f = Path(str(base) + ".png")
        f.write_bytes(png_bytes(4, 5))
        return f

    monkeypatch.setattr(visuals, "download", fake_download)
    p = write_prompts(tmp_path, 2)
    rc = visuals.main(["generate", "--provider", "fal", "--prompts", str(p), "--out", str(tmp_path / "art")])
    assert rc == 1
    log = json.loads((tmp_path / "art" / "generation.json").read_text(encoding="utf-8"))
    assert [r["status"] for r in log] == ["ok", "failed"]
    assert log[0]["file"] == "slide-01.png" and log[0]["pixels"] == "4x5"
    assert "422" in log[1]["error"]


# ---------- browser + real render (skipped without a browser) ----------

def test_browser_override(tmp_path, monkeypatch):
    fake = tmp_path / "chrome"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("BBM_BROWSER", str(fake))
    assert visuals.find_browser() == fake
    monkeypatch.setenv("BBM_BROWSER", str(tmp_path / "missing"))
    assert visuals.find_browser(required=False) is None


@pytest.mark.skipif(visuals.find_browser(required=False) is None, reason="no Chrome/Edge/Chromium installed")
def test_real_render_png_and_pdf(tmp_path):
    src = tmp_path / "s.html"
    assert run("scaffold", "--kind", "carousel", "--out", src, "--size", "540x675").returncode == 0
    r = run("render", src, "--out", tmp_path / "out", "--size", "540x675", "--pdf", "c.pdf")
    assert r.returncode == 0, r.stderr
    pngs = sorted((tmp_path / "out").glob("slide-*.png"))
    assert len(pngs) == 5
    assert all(visuals.image_size(p) == (540, 675) for p in pngs)
    pdf = (tmp_path / "out" / "c.pdf").read_bytes()
    assert pdf.startswith(b"%PDF")
    import re
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 5
    assert not list(tmp_path.glob(".render-*"))
    r = run("pdf", str(tmp_path / "out" / "slide-*.png"), "--out", tmp_path / "imgs.pdf", "--size", "540x675")
    assert r.returncode == 0, r.stderr
    assert len(re.findall(rb"/Type\s*/Page\b", (tmp_path / "imgs.pdf").read_bytes())) == 5
