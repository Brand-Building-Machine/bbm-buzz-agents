"""Offline checks for email-followups: every example passes the shared checker, no dashes anywhere.

Run from outside the skill folder:
    cd /tmp && python3 -m pytest <abs path>/tests -q -p no:cacheprovider
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True  # keep __pycache__ out of the shared scripts folder

SKILL_DIR = Path(__file__).resolve().parent.parent
KIT_PATH = SKILL_DIR.parent / "email-sequences" / "scripts" / "emailkit.py"
PLAYBOOKS = SKILL_DIR / "references" / "playbooks.md"
REPLIES = SKILL_DIR / "references" / "replies.md"
DASHES = re.compile("[\u2014\u2013]")


def load_kit():
    spec = importlib.util.spec_from_file_location("emailkit_for_followups", KIT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


KIT = load_kit()


def fenced(path, lang):
    text = path.read_text(encoding="utf-8")
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


EXAMPLES = [b for b in fenced(PLAYBOOKS, "markdown") if b.startswith("---")]


def kind_of(block):
    m = re.search(r"^kind:\s*(\S+)", block, re.M)
    return m.group(1) if m else ""


def test_one_example_per_followup_kind():
    kinds = sorted(kind_of(b) for b in EXAMPLES)
    assert kinds == sorted(KIT.FOLLOWUP_KINDS)


@pytest.mark.parametrize("block", EXAMPLES, ids=[kind_of(b) for b in EXAMPLES])
def test_example_passes_checker(block):
    result = KIT.check_text(block)
    assert result["errors"] == [], result["errors"]
    assert result["kind"] in KIT.FOLLOWUP_KINDS


@pytest.mark.parametrize("block", fenced(REPLIES, "text"))
def test_reply_examples_have_no_banned_phrases(block):
    low = re.sub("[\u2018\u2019]", "'", block.lower())
    hits = [p for p in KIT.BANNED if p in low]
    assert hits == []
    assert not KIT.SLOT.search(block)


def test_notes_before_first_email_are_ignored_by_checker():
    # SKILL.md tells the agent to put owner notes between the title and Email 1.
    block = next(b for b in EXAMPLES if "Notes for the owner" in b)
    front, emails, _ = KIT.parse(block)
    assert all("Notes for the owner" not in e["body"] for e in emails)


def test_cadence_rules_are_enforced():
    base = "---\nkind: no-show\nbusiness: B\naudience: A\ntrigger: T\ngoal: G\nexit: any reply\nstatus: draft\n---\n# T\n"
    email = "## Email {n}: job\nSend: Day {d}\nSubject: s{n}\nCTA: c\n\nBody text here.\n\nSam\n\n"
    too_close = base + email.format(n=1, d=0) + email.format(n=2, d=1)
    assert any("under 2 days" in e for e in KIT.check_text(too_close)["errors"])
    too_many = base + "".join(email.format(n=i, d=i * 3) for i in range(1, 7))
    assert any("stop at 5" in e for e in KIT.check_text(too_many)["errors"])


def test_skill_frontmatter_name():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: email-followups\n")
    assert "\ndescription: " in text.split("\n---", 2)[0] + "\n"


def test_no_em_or_en_dashes_anywhere():
    bad = []
    for p in SKILL_DIR.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            if DASHES.search(p.read_text(encoding="utf-8", errors="ignore")):
                bad.append(str(p.relative_to(SKILL_DIR)))
    assert bad == []
