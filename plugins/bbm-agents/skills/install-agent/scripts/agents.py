#!/usr/bin/env python3
"""Render prebuilt bbm-agents personas and open owner-reviewed Buzz drafts.

Stdlib only; works on macOS, Linux and Windows.

  agents.py list
  agents.py config                         # show which config file is in use and its values
  agents.py render <role> [--config PATH]  # print the rendered persona (no frontmatter)
  agents.py draft  <role> --channel UUID [--update "Existing Name"] [--config PATH] [--dry-run]
  agents.py status [--config PATH]         # installed version vs plugin version, per role

Exit codes: 0 ok, 2 unresolved placeholders / missing config, 3 buzz CLI failure.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
PERSONAS = PLUGIN_ROOT / "personas"
POINTER = Path.home() / ".bbm-agents.json"   # machine-local: {"config": "<abs path>"}
CONFIG_NAME = "buzz-agents.config.json"
STAMP_RE = re.compile(r"<!-- bbm-agents: ([a-z0-9-]+) v(\d+) -->")
SLOT_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
IF_RE = re.compile(r"\{\{#if ([A-Z_]+)\}\}\n?(.*?)\{\{/if\}\}\n?", re.S)


# ---------- personas ----------

def parse_persona(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        body = body.lstrip("\n")
    return meta, body


def all_personas():
    out = {}
    for p in sorted(PERSONAS.glob("*.md")):
        meta, body = parse_persona(p)
        out[meta.get("role", p.stem)] = (meta, body)
    return out


# ---------- config ----------

def find_config(explicit=None):
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("BUZZ_AGENTS_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    if POINTER.exists():
        try:
            return Path(json.loads(POINTER.read_text(encoding="utf-8"))["config"]).expanduser()
        except (ValueError, KeyError):
            pass
    for d in [Path.cwd(), *Path.cwd().parents]:
        if (d / CONFIG_NAME).exists():
            return d / CONFIG_NAME
    return None


def load_config(explicit=None):
    path = find_config(explicit)
    if not path or not path.exists():
        sys.stderr.write(
            "No buzz-agents config found. Run the workspace-config skill first "
            f"(it writes {CONFIG_NAME} into the owner's workspace and records it in {POINTER}).\n")
        sys.exit(2)
    values = json.loads(path.read_text(encoding="utf-8"))
    return path, {k: ("" if v is None else str(v)) for k, v in values.items()}


# ---------- rendering ----------

def fill(text, values):
    def cond(m):
        return m.group(2) if values.get(m.group(1), "").strip() else ""
    text = IF_RE.sub(cond, text)
    return SLOT_RE.sub(lambda m: values.get(m.group(1), m.group(0)) or m.group(0), text)


def render(role, values):
    personas = all_personas()
    if role not in personas:
        sys.stderr.write(f"Unknown role '{role}'. Available: {', '.join(personas)}\n")
        sys.exit(2)
    meta, body = personas[role]
    body = fill(body, values).rstrip() + "\n"
    display = fill(meta.get("display_name", role), values)
    missing = sorted(set(SLOT_RE.findall(body)) | set(SLOT_RE.findall(display)))
    if missing:
        sys.stderr.write("Unresolved placeholders: " + ", ".join(missing) +
                         "\nAdd them to the config (workspace-config skill). Nothing was drafted.\n")
        sys.exit(2)
    stamp = f"<!-- bbm-agents: {role} v{meta.get('version', '1')} -->"
    return display, fill(meta.get("description", ""), values), f"{body}\n{stamp}\n"


# ---------- buzz ----------

def buzz_bin():
    exe = shutil.which("buzz")
    if exe:
        return exe
    for cand in ["/Applications/Buzz.app/Contents/MacOS/buzz",
                 os.path.expandvars(r"%LOCALAPPDATA%\Programs\Buzz\buzz.exe")]:
        if Path(cand).exists():
            return cand
    return None


def managed_agents_file():
    cands = [
        Path.home() / "Library/Application Support/xyz.block.buzz.app/agents/managed-agents.json",
        Path(os.environ.get("APPDATA", "")) / "xyz.block.buzz.app/agents/managed-agents.json",
        Path(os.environ.get("LOCALAPPDATA", "")) / "xyz.block.buzz.app/agents/managed-agents.json",
        Path.home() / ".local/share/xyz.block.buzz.app/agents/managed-agents.json",
    ]
    return next((c for c in cands if c.is_file()), None)


def installed_agents():
    f = managed_agents_file()
    if not f:
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    recs = data if isinstance(data, list) else data.get("agents", data)
    if isinstance(recs, dict):
        recs = list(recs.values())
    return recs


# ---------- commands ----------

def cmd_list(_):
    for role, (meta, _) in all_personas().items():
        print(f"{role:16} v{meta.get('version', '1'):3} runtimes={meta.get('runtimes', '?'):18} {meta.get('description', '')}")


def cmd_config(a):
    path, values = load_config(a.config)
    print(f"config: {path}")
    for k, v in values.items():
        print(f"  {k} = {v}")


def cmd_render(a):
    _, values = load_config(a.config)
    display, desc, prompt = render(a.role, values)
    print(f"# name: {display}\n# description: {desc}\n")
    sys.stdout.write(prompt)


def cmd_draft(a):
    _, values = load_config(a.config)
    display, desc, prompt = render(a.role, values)
    if a.update:
        args = ["agents", "draft-update", "--channel", a.channel, "--agent-name", a.update,
                "--display-name", display, "--system-prompt", "-"]
    else:
        args = ["agents", "draft-create", "--channel", a.channel,
                "--display-name", display, "--system-prompt", "-"]
    if a.dry_run:
        print("DRY RUN: buzz " + " ".join(args))
        print(f"# name: {display}\n# description: {desc}\n")
        sys.stdout.write(prompt)
        return
    exe = buzz_bin()
    if not exe:
        sys.stderr.write("buzz CLI not found. Give the owner the manual-paste fallback below.\n")
        print(f"# name: {display}\n# description: {desc}\n")
        sys.stdout.write(prompt)
        sys.exit(3)
    r = subprocess.run([exe, *args], input=prompt, text=True, capture_output=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.stderr.write("\nDraft failed. Give the owner the manual-paste fallback (run `render`).\n")
        sys.exit(3)
    print(f"\nDraft sent for '{display}'. It is NOT an agent until the owner saves it in Buzz Desktop.")


def cmd_status(a):
    personas = all_personas()
    recs = installed_agents()
    if recs is None:
        print("Could not find Buzz's managed-agents.json on this machine; installed versions unknown.")
        recs = []
    found = {}
    for r in recs:
        m = STAMP_RE.search(r.get("system_prompt") or "")
        if m:
            found.setdefault(m.group(1), []).append((r.get("display_name") or r.get("name"), int(m.group(2))))
    for role, (meta, _) in personas.items():
        latest = int(meta.get("version", "1"))
        if role not in found:
            print(f"{role:16} not installed from this plugin (latest v{latest})")
        for name, v in found.get(role, []):
            state = "up to date" if v >= latest else f"UPDATE AVAILABLE v{v} -> v{latest}"
            print(f"{role:16} '{name}' v{v}: {state}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in [("config", cmd_config), ("status", cmd_status)]:
        s = sub.add_parser(name); s.add_argument("--config"); s.set_defaults(fn=fn)
    s = sub.add_parser("render"); s.add_argument("role"); s.add_argument("--config"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("draft"); s.add_argument("role"); s.add_argument("--channel", required=True)
    s.add_argument("--update", metavar="EXISTING_NAME"); s.add_argument("--config")
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_draft)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
