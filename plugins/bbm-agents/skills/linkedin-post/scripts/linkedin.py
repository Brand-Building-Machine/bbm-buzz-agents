#!/usr/bin/env python3
"""LinkedIn Desk helper. Stdlib only; macOS, Linux, Windows.

Paths, the owner's LinkedIn profile, the story bank, dated work folders, and a deterministic
checker for post copy and carousel slides. Judgement (what to write) is the agent's job.
Nothing here talks to LinkedIn; nothing is ever posted.

  linkedin.py paths [--business NAME]            # drafts folder, brand files, profile, story bank, visuals engine
  linkedin.py profile init|check [--business NAME]  # linkedin.json next to the brand files (init never overwrites)
  linkedin.py stories init [--business NAME]     # linkedin-stories.md story bank template (never overwrites)
  linkedin.py new post|carousel|image|plan --slug TEXT [--business NAME]
                                                 # create and print a dated work folder
  linkedin.py lint FILE [--json]                 # FILE = post markdown (## Post sections) or slides.json

Exit codes: 0 ok, 1 check failed, 2 config or usage problem.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
VISUALS = SKILLS / "social-visuals" / "scripts" / "visuals.py"
POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
PROFILE_NAME = "linkedin.json"
STORIES_NAME = "linkedin-stories.md"
BRAND_FILES = ["brand-bible.md", "voice-agent.md", "offers.md", "root.css"]
KINDS = ["post", "carousel", "image", "plan"]
ROUTES = ["html", "image", "hybrid"]
PROVIDERS = ["fal", "higgsfield"]

POST_MAX = 3000          # LinkedIn's character limit for a post
FOLD_CHARS = 140         # roughly what shows on a phone before "...see more"
HASHTAG_MAX = 3
SLIDES_MIN, SLIDES_MAX = 5, 12
COVER_WORDS, HEADLINE_WORDS, BODY_WORDS = 8, 10, 30
VOCAB_PER_PARA = 3

PROFILE_TEMPLATE = {
    "author": "",
    "author_line": "",
    "page": "personal",
    "audience": "",
    "goal": "",
    "pillars": ["", "", ""],
    "posts_per_week": 3,
    "offer_cta": "",
    "visuals": {"default": "html", "provider": "", "model": "", "size": "1080x1350"},
    "avoid": [],
}

STORIES_TEMPLATE = """# LinkedIn story bank: {name}

Real material only. Every line here was said or confirmed by the owner. Skills quote from this file
instead of asking the same question twice, and never invent anything that isn't in it.

## Receipts
<!-- Numbers with a referent: what, when, how much. "$4,730 of rework on the Hale job, March 2026". -->

## Stories
<!-- One per heading: what happened, when, who (with permission), what changed. -->

## Positions
<!-- Things the owner believes about their industry and would defend in the comments. -->

## Scars
<!-- Mistakes, losses, things that broke. Stated flat, with a date. -->

## Their words
<!-- 3-5 LinkedIn posts or emails the owner wrote themselves, pasted whole. The voice reference. -->

## Off limits
<!-- Clients, people, topics and numbers never to mention. -->
"""

# ---------- copy rules ----------
# AI-tell patterns adapted from sergebulaev/linkedin-skills (MIT) and the 2026 AI-tell consensus lists.
FORENSIC = [r"\boaicite\b", r"contentReference", r"turn0search\d", r"\bas an ai\b",
            r"as of my (last|knowledge) (update|cutoff)", r"\[your name\]", r"\{\{[A-Z_]+\}\}"]
BRIDGES = [r"\bthe result\?", r"\bplot twist\b", r"\bhere'?s the thing\b", r"\blet that sink in\b",
           r"\bwhat nobody tells you\b", r"\bwhat most people miss\b", r"\bthe real question is\b",
           r"\bthis is where it gets interesting\b", r"\bthat'?s the real story\b"]
SINCERITY = [r"\blet me be (honest|real|clear)\b", r"\bi'?ll be (honest|real)\b", r"\breal talk\b",
             r"\bhonestly\?", r"\bunpopular opinion\b", r"\bcan i be vulnerable\b", r"\bconfession:"]
CONTRAST = [r"\bit'?s not (just )?[^.?!\n]{1,40}?[,.;] it'?s\b", r"\bisn'?t [^.?!\n]{1,40}?\. it'?s\b",
            r"\bstop [^.?!\n]{1,30}?\. start\b", r"\bno [^.?!\n]{1,20}?\. no [^.?!\n]{1,20}?\. just\b"]
OPENERS = [r"^here'?s (what|how|why)\b", r"^in today'?s\b", r"^stop\b", r"^i'?m (thrilled|excited|humbled)\b"]
BAIT = [r"\bcomment ['\"]?[A-Z]{2,}['\"]? (below|and i'?ll)", r"\btag someone\b", r"\bwhat do you think\?\s*$",
        r"\bagree\?\s*$", r"\bthoughts\?\s*$", r"\bsmash (that )?like\b"]
VOCAB = ["significant", "crucial", "notably", "comprehensive", "insights", "robust", "leverage",
         "foster", "landscape", "nuanced", "multifaceted", "holistic", "streamline", "elevate",
         "empower", "delve", "tapestry", "realm", "seamless", "unlock", "harness", "game-changer",
         "navigate", "journey", "paradigm", "ecosystem", "synergy", "transformative", "pivotal"]
VOCAB_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in VOCAB) + r")\b", re.I)
PLACEHOLDER_RE = re.compile(r"\[(client to provide|insert[^\]]*|name|number|todo[^\]]*|tbd)\]", re.I)
LINK_RE = re.compile(r"https?://\S+|\bwww\.\S+", re.I)
HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-z][\w]*")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


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
    for key in ("PROPOSED_PATH", "BRAND_PATH"):
        if not cfg.get(key):
            die(f"Config has no {key}. Run workspace-config to add it.")
    return cfg


def brand_dir(cfg, business):
    pattern = cfg["BRAND_PATH"]
    if "{business}" in pattern:
        if not business:
            die("This workspace keeps brand folders per business. Pass --business <name>.")
        return Path(pattern.replace("{business}", business)).expanduser()
    return Path(pattern).expanduser()


def out_dir(cfg, business):
    base = Path(cfg["PROPOSED_PATH"]).expanduser() / "linkedin"
    return base / business if business and "{business}" in cfg["BRAND_PATH"] else base


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48].strip("-") or "untitled"


# ---------- profile ----------

def profile_problems(p):
    probs = []
    if not str(p.get("author", "")).strip():
        probs.append("author: whose name goes on the posts and slides")
    if not str(p.get("audience", "")).strip():
        probs.append("audience: who the posts are for, in one line")
    pillars = [x for x in p.get("pillars") or [] if str(x).strip()]
    if len(pillars) < 2:
        probs.append("pillars: at least 2 topics they post about")
    if p.get("page") not in ("personal", "company"):
        probs.append("page: 'personal' or 'company'")
    v = p.get("visuals") or {}
    if v.get("default") not in ROUTES:
        probs.append(f"visuals.default: one of {', '.join(ROUTES)}")
    elif v["default"] in ("image", "hybrid") and v.get("provider") not in PROVIDERS:
        probs.append(f"visuals.provider: {' or '.join(PROVIDERS)} (needed for the '{v['default']}' route)")
    if v.get("size") and not re.fullmatch(r"\d{3,4}x\d{3,4}", str(v["size"])):
        probs.append("visuals.size: WIDTHxHEIGHT, e.g. 1080x1350")
    return probs


# ---------- lint ----------

def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def first_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def find_all(patterns, text, flags=re.I | re.M):
    hits = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags):
            hits.append(m.group(0).strip())
    return hits


def lint_text(text, where="post"):
    """Return (errors, warnings, stats) for one post body."""
    errors, warnings = [], []
    if "—" in text:
        errors.append(f"{where}: em dash (—) x{text.count(chr(0x2014))}. Use a comma, colon, full stop or parentheses.")
    if re.search(r"\w – \w|\w -- \w", text):
        warnings.append(f"{where}: dash between clauses (– or --). Rewrite with a comma or full stop.")
    for hit in find_all(FORENSIC, text):
        errors.append(f"{where}: model leakage {hit!r}. Remove it.")
    n = len(text)
    if n > POST_MAX:
        errors.append(f"{where}: {n} characters; LinkedIn allows {POST_MAX}.")
    fl = first_line(text)
    if fl.endswith("?"):
        warnings.append(f"{where}: opens with a question. Lead with the number or the fact; move the question to the end.")
    if len(fl) > FOLD_CHARS:
        warnings.append(f"{where}: first line is {len(fl)} characters; phones cut off around {FOLD_CHARS} before '...see more'.")
    for hit in find_all(OPENERS, fl):
        warnings.append(f"{where}: stock opener {hit!r}.")
    for hit in find_all(BRIDGES, text):
        warnings.append(f"{where}: reveal/teaser phrase {hit!r}. Say the thing plainly.")
    for hit in find_all(SINCERITY, text):
        warnings.append(f"{where}: sincerity announcement {hit!r}. State the fact flat, no frame.")
    contrasts = find_all(CONTRAST, text)
    if len(contrasts) > 1:
        warnings.append(f"{where}: {len(contrasts)} 'not X, it's Y' style contrasts; keep one at most.")
    for hit in find_all(BAIT, text):
        warnings.append(f"{where}: engagement bait {hit!r}. End with a specific question or a clean line.")
    for i, para in enumerate(paragraphs(text), 1):
        words = VOCAB_RE.findall(para)
        if len(words) >= VOCAB_PER_PARA:
            warnings.append(f"{where}: paragraph {i} has {len(words)} AI-tell words "
                            f"({', '.join(sorted(set(w.lower() for w in words)))}). Rewrite it plainly.")
    frag_run, worst = 0, 0
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = s.strip()
        if not s:
            continue
        frag_run = frag_run + 1 if len(s.split()) <= 3 else 0
        worst = max(worst, frag_run)
    if worst >= 3:
        warnings.append(f"{where}: {worst} very short fragments in a row. Merge them into sentences.")
    links = LINK_RE.findall(text)
    if links:
        warnings.append(f"{where}: link in the post body ({links[0][:40]}). Put links in the first comment.")
    tags = HASHTAG_RE.findall(text)
    if len(tags) > HASHTAG_MAX:
        warnings.append(f"{where}: {len(tags)} hashtags; use {HASHTAG_MAX} or fewer.")
    for hit in PLACEHOLDER_RE.findall(text):
        warnings.append(f"{where}: placeholder [{hit}] still to fill before posting.")
    return errors, warnings, {"chars": n, "first_line_chars": len(fl), "hashtags": len(tags)}


def post_sections(md):
    """Text of every '## Post...' section; the whole file if there are none."""
    parts = re.split(r"(?m)^##\s+", md)
    found = []
    for part in parts[1:]:
        title, _, body = part.partition("\n")
        if re.match(r"post\b", title.strip(), re.I):
            found.append((title.strip(), body.strip()))
    return found or [("post", md.strip())]


def words(s):
    return len(re.findall(r"\S+", s or ""))


def lint_slides(data):
    errors, warnings = [], []
    slides = data.get("slides") or []
    route = data.get("route", "html")
    if route not in ROUTES:
        errors.append(f"route must be one of {', '.join(ROUTES)}.")
    if not slides:
        errors.append("no slides.")
        return errors, warnings, {"slides": 0}
    if not SLIDES_MIN <= len(slides) <= SLIDES_MAX:
        warnings.append(f"{len(slides)} slides; {SLIDES_MIN}-{SLIDES_MAX} is the usual range. Cut filler or split it.")
    if slides[0].get("role") != "cover":
        warnings.append("slide 1 should be the cover (role: cover).")
    if slides[-1].get("role") not in ("close", "cta"):
        warnings.append("the last slide should close (role: close) with one action.")
    for i, s in enumerate(slides, 1):
        head, body = s.get("headline", ""), s.get("body", "")
        text = f"{head}\n{body}"
        if "—" in text:
            errors.append(f"slide {i}: em dash. Rewrite.")
        limit = COVER_WORDS if i == 1 else HEADLINE_WORDS
        if words(head) > limit:
            warnings.append(f"slide {i}: headline is {words(head)} words; keep it to {limit}.")
        if words(body) > BODY_WORDS:
            warnings.append(f"slide {i}: {words(body)} words of body; one idea per slide, {BODY_WORDS} words max.")
        if not head.strip() and not body.strip() and route == "html":
            warnings.append(f"slide {i}: no text.")
        if route in ("image", "hybrid") and not str(s.get("prompt", "")).strip():
            warnings.append(f"slide {i}: route is {route}; write its image prompt before generating.")
        for hit in PLACEHOLDER_RE.findall(text):
            warnings.append(f"slide {i}: placeholder [{hit}] still to fill.")
    m = re.match(r"\s*(\d{1,2})\b", slides[0].get("headline", ""))
    points = [s for s in slides if s.get("role") == "point"]
    if m and len(points) >= 2 and int(m.group(1)) != len(points):
        warnings.append(f"the cover promises {m.group(1)} but there are {len(points)} point slides. Deliver the exact count.")
    return errors, warnings, {"slides": len(slides), "route": route}


def cmd_lint(path, as_json):
    p = Path(path)
    if not p.exists():
        die(f"No such file: {p}")
    raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
        except ValueError as e:
            die(f"{p} is not valid JSON: {e}")
        errors, warnings, stats = lint_slides(data)
        if data.get("post"):
            e2, w2, s2 = lint_text(data["post"], "post text")
            errors += e2
            warnings += w2
            stats["post_chars"] = s2["chars"]
    else:
        errors, warnings, stats = [], [], {}
        for title, body in post_sections(raw):
            e, w, s = lint_text(body, title)
            errors += e
            warnings += w
            stats[title] = s
    result = {"file": str(p), "errors": errors, "warnings": warnings, "stats": stats,
              "ok": not errors}
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        for e in errors:
            print(f"ERROR  {e}")
        for w in warnings:
            print(f"warn   {w}")
        print(f"{'OK' if not errors else 'FAIL'}: {len(errors)} error(s), {len(warnings)} warning(s). {json.dumps(stats)}")
    return 0 if not errors else 1


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("paths",):
        s = sub.add_parser(name)
        s.add_argument("--business")
    pr = sub.add_parser("profile")
    pr.add_argument("action", choices=["init", "check"])
    pr.add_argument("--business")
    st = sub.add_parser("stories")
    st.add_argument("action", choices=["init"])
    st.add_argument("--business")
    nw = sub.add_parser("new")
    nw.add_argument("kind", choices=KINDS)
    nw.add_argument("--slug", required=True)
    nw.add_argument("--business")
    ln = sub.add_parser("lint")
    ln.add_argument("file")
    ln.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "lint":
        return cmd_lint(a.file, a.json)

    cfg = load_config()
    bdir = brand_dir(cfg, a.business)
    if a.cmd == "paths":
        present = [f for f in BRAND_FILES if (bdir / f).exists()]
        missing = [f for f in BRAND_FILES if f not in present]
        info = {
            "drafts": str(out_dir(cfg, a.business)),
            "brand_folder": str(bdir),
            "brand_files_present": present,
            "brand_files_missing": missing,
            "root_css": str(bdir / "root.css") if (bdir / "root.css").exists() else None,
            "logo": next((str(bdir / n) for n in ("logo.svg", "logo.png") if (bdir / n).exists()), None),
            "profile": str(bdir / PROFILE_NAME),
            "profile_exists": (bdir / PROFILE_NAME).exists(),
            "story_bank": str(bdir / STORIES_NAME),
            "story_bank_exists": (bdir / STORIES_NAME).exists(),
            "visuals_script": str(VISUALS),
            "workspace_map": cfg.get("WORKSPACE_MAP"),
        }
        print(json.dumps(info, indent=2))
        if missing:
            print(f"Missing brand files: {', '.join(missing)}. Run brand-bible first.", file=sys.stderr)
        return 0
    if a.cmd == "profile":
        path = bdir / PROFILE_NAME
        if a.action == "init":
            if path.exists():
                print(f"{path} already exists; left as is.")
                return 0
            bdir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(PROFILE_TEMPLATE, indent=2) + "\n", encoding="utf-8")
            print(f"Created {path}. Fill it in with the owner.")
            return 0
        if not path.exists():
            die(f"No LinkedIn profile at {path}. Run `linkedin.py profile init` and fill it in with the owner.", 1)
        try:
            prof = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            die(f"{path} is not valid JSON: {e}")
        probs = profile_problems(prof)
        if probs:
            print("Profile incomplete:")
            for p in probs:
                print(f"  - {p}")
            return 1
        print(f"Profile complete: {path}")
        return 0
    if a.cmd == "stories":
        path = bdir / STORIES_NAME
        if path.exists():
            print(f"{path} already exists; left as is.")
            return 0
        bdir.mkdir(parents=True, exist_ok=True)
        name = cfg.get("OWNER_NAME") or "owner"
        path.write_text(STORIES_TEMPLATE.format(name=name), encoding="utf-8")
        print(f"Created {path}.")
        return 0
    if a.cmd == "new":
        d = out_dir(cfg, a.business) / f"{dt.date.today().isoformat()}-{a.kind}-{slugify(a.slug)}"
        n = 2
        base = d
        while d.exists():
            d = Path(f"{base}-{n}")
            n += 1
        d.mkdir(parents=True)
        print(d)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
