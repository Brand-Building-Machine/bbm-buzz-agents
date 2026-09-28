"""Portability guard: no absolute / machine-specific paths baked into the skill.

The skill must run on any operator's machine. Scripts and SKILL.md must never
contain an absolute home path. (Tests are excluded — this file necessarily
contains the offending substrings.)
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD = ("/Users/", "/home/", "C:\\")
SKIP_DIRS = {"__pycache__", ".pytest_cache", "tests"}
SCAN_EXTS = {".py", ".md"}


def test_no_absolute_machine_paths():
    offenders = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix not in SCAN_EXTS:
            continue
        text = p.read_text(errors="ignore")
        for bad in BAD:
            if bad in text:
                offenders.append(f"{p.relative_to(ROOT)} contains {bad!r}")
    assert offenders == [], "absolute machine paths found:\n" + "\n".join(offenders)
