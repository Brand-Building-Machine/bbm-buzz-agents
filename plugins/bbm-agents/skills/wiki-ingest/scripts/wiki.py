#!/usr/bin/env python3
"""Deterministic helpers for the wiki skills. Stdlib only; macOS, Linux, Windows.

Reads folder locations from the owner's buzz-agents config (same lookup as install-agent).

  wiki.py paths                     # resolved knowledge paths + whether each exists
  wiki.py init                      # create missing wiki folders, index.md, log.md (never overwrites)
  wiki.py unprocessed               # raw sources with status: unprocessed (oldest first)
  wiki.py lint [--stale-days 7]     # structural audit: orphans, stale sources, broken related:, dead wikilinks
  wiki.py lint --json               # same, machine-readable

Exit codes: 0 ok, 2 missing config/paths.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
WIKI_KINDS = ("entities", "concepts", "topics")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FENCE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------- config ----------

def find_config():
    env = os.environ.get("BUZZ_AGENTS_CONFIG")
    if env:
        return Path(env).expanduser()
    if POINTER.exists():
        try:
            return Path(json.loads(POINTER.read_text(encoding="utf-8"))["config"]).expanduser()
        except (ValueError, KeyError):
            pass
    for d in [Path.cwd(), *Path.cwd().parents]:
        if (d / CONFIG_NAME).exists():
            return d / CONFIG_NAME
    return None


def load_paths():
    cfg_path = find_config()
    if not cfg_path or not cfg_path.exists():
        sys.stderr.write("No buzz-agents config found. Run the workspace-config skill first.\n")
        sys.exit(2)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    root = Path(cfg.get("WORKSPACE_ROOT", "")).expanduser()
    need = ["RAW_SOURCES_PATH", "WIKI_PATH", "STATE_PATH"]
    missing = [k for k in need if not cfg.get(k)]
    if missing:
        sys.stderr.write("Config is missing: " + ", ".join(missing) +
                         ". Run workspace-config to add the knowledge paths.\n")
        sys.exit(2)
    wiki = Path(cfg["WIKI_PATH"]).expanduser()
    return {
        "config": cfg_path,
        "root": root,
        "raw": Path(cfg["RAW_SOURCES_PATH"]).expanduser(),
        "wiki": wiki,
        "index": Path(cfg.get("WIKI_INDEX") or wiki / "index.md").expanduser(),
        "log": Path(cfg.get("WIKI_LOG") or wiki / "log.md").expanduser(),
        "state": Path(cfg["STATE_PATH"]).expanduser(),
        "scope_pattern": cfg.get("SCOPE_STATE_PATTERN", ""),
    }


# ---------- markdown helpers ----------

def frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    meta, key = {}, None
    for line in text[3:end].splitlines():
        if re.match(r"^[A-Za-z_][\w-]*:", line):
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            else:
                meta[key] = val.strip("'\"")
        elif key and line.strip().startswith("- "):
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.strip()[2:].strip().strip("'\""))
    return meta


def md_files(root):
    if not root.exists():
        return []
    return [p for p in root.rglob("*.md") if not any(part.startswith(".") for part in p.relative_to(root).parts)]


def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# ---------- commands ----------

def cmd_paths(_):
    P = load_paths()
    for k in ("config", "root", "raw", "wiki", "index", "log", "state"):
        print(f"{k:8} {'ok     ' if P[k].exists() else 'MISSING'} {P[k]}")
    if P["scope_pattern"]:
        print(f"scopes   pattern  {P['scope_pattern']}")


INDEX_TMPL = """---
title: "Knowledge Index"
type: index
---

# Knowledge Index

The map of this workspace's wiki. `wiki-ingest` keeps it current; `wiki-ask` reads it first.

## Entities

## Concepts

## Topics

## Recent sources
"""

LOG_TMPL = """---
title: "Knowledge Log"
type: log
---

# Knowledge Log

Append-only. One entry per ingest, query or audit, newest at the bottom.
"""


def cmd_init(_):
    P = load_paths()
    made = []
    for d in [P["raw"], P["wiki"], *(P["wiki"] / k for k in WIKI_KINDS), P["state"]]:
        if not d.exists():
            d.mkdir(parents=True)
            made.append(str(d))
    for f, body in ((P["index"], INDEX_TMPL), (P["log"], LOG_TMPL)):
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
            made.append(str(f))
    print("created:\n  " + "\n  ".join(made) if made else "nothing to create; structure already exists")


def cmd_unprocessed(_):
    P = load_paths()
    rows = []
    for p in md_files(P["raw"]):
        m = frontmatter(read(p))
        if m.get("status") in ("unprocessed", "needs-review"):
            rows.append((m.get("date_captured") or m.get("date") or "", m.get("status"), p))
    rows.sort(key=lambda r: (r[0], str(r[2])))
    if not rows:
        print("no unprocessed sources")
    for date, status, p in rows:
        print(f"{date or '????-??-??'}  {status:12}  {p}")


def cmd_lint(a):
    P = load_paths()
    root = P["root"] if P["root"].exists() else P["wiki"]
    all_md = md_files(root)
    texts = {p: read(p) for p in all_md}
    stems = {p.stem.lower() for p in all_md}
    titles = set()
    ids = set()
    for p, t in texts.items():
        m = frontmatter(t)
        if m.get("title"):
            titles.add(str(m["title"]).lower())
        if m.get("id"):
            ids.add(str(m["id"]))

    def link_targets(t):
        return [x.strip() for x in LINK_RE.findall(FENCE_RE.sub("", t))]

    inbound = {}
    for p, t in texts.items():
        for tgt in link_targets(t):
            inbound.setdefault(Path(tgt).name.lower(), set()).add(p)
            inbound.setdefault(tgt.lower(), set()).add(p)

    findings = {"orphans": [], "stale_sources": [], "broken_related": [], "dead_links": []}

    # 1 orphans: wiki pages nothing links to (index counts as a link)
    for kind in WIKI_KINDS:
        for p in md_files(P["wiki"] / kind):
            key = p.stem.lower()
            rel = str(p.relative_to(P["wiki"]).with_suffix("")).replace(os.sep, "/").lower()
            srcs = (inbound.get(key, set()) | inbound.get(rel, set())) - {p}
            if not srcs:
                findings["orphans"].append(str(p))

    # 2 stale unprocessed sources
    cutoff = dt.date.today() - dt.timedelta(days=a.stale_days)
    for p in md_files(P["raw"]):
        m = frontmatter(texts.get(p) or read(p))
        if m.get("status") != "unprocessed":
            continue
        d = str(m.get("date_captured") or m.get("date") or "")[:10]
        try:
            if dt.date.fromisoformat(d) < cutoff:
                findings["stale_sources"].append(f"{p} (captured {d})")
        except ValueError:
            findings["stale_sources"].append(f"{p} (no valid date_captured)")

    # 3 broken related: ids
    for p, t in texts.items():
        rel = frontmatter(t).get("related")
        for r in (rel if isinstance(rel, list) else []):
            if re.match(r"^[A-Z]{2,5}-", r) and r not in ids:
                findings["broken_related"].append(f"{p} -> {r}")

    # 4 dead wikilinks
    for p, t in texts.items():
        for tgt in link_targets(t):
            name = Path(tgt).name.lower()
            full = (root / tgt).with_suffix(".md") if "/" in tgt else None
            if name in stems or tgt.lower() in titles or tgt in ids or (full and full.exists()):
                continue
            findings["dead_links"].append(f"{p} -> [[{tgt}]]")

    if a.json:
        print(json.dumps(findings, indent=2))
        return
    for k, v in findings.items():
        print(f"\n## {k.replace('_', ' ')} ({len(v)})")
        for line in v[:200]:
            print(f"- {line}")
        if len(v) > 200:
            print(f"- ... {len(v) - 200} more")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n, f in (("paths", cmd_paths), ("init", cmd_init), ("unprocessed", cmd_unprocessed)):
        sub.add_parser(n).set_defaults(fn=f)
    s = sub.add_parser("lint")
    s.add_argument("--stale-days", type=int, default=7)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_lint)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
