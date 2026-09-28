"""Offline tests for email-onboarding. Run from outside the skill folder:
python3 -m pytest <abs path>/tests -q -p no:cacheprovider
"""
import importlib.util
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
EMAILKIT = SKILL.parent / "email-sequences" / "scripts" / "emailkit.py"
FENCE = re.compile(r"^```markdown\n(---\n.*?)^```", re.M | re.S)
DASHES = re.compile("[\u2014\u2013]")
ABS_PATH = re.compile("/" + "Users/|[A-Z]:\\\\" + "Users")


def load_emailkit():
    spec = importlib.util.spec_from_file_location("emailkit", EMAILKIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def draft_blocks():
    blocks = []
    for ref in sorted((SKILL / "references").glob("*.md")):
        for m in FENCE.finditer(ref.read_text(encoding="utf-8")):
            blocks.append((ref.name, m.group(1)))
    return blocks


def skill_files():
    return [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]


def test_emailkit_is_where_the_skill_says():
    assert EMAILKIT.exists(), f"shared checker missing: {EMAILKIT}"


def test_examples_exist():
    blocks = draft_blocks()
    assert len(blocks) >= 2, "sequence.md should hold the main sequence and the reminders as draft-format examples"


def test_every_example_passes_the_checker():
    ek = load_emailkit()
    for name, text in draft_blocks():
        r = ek.check_text(text)
        assert not r["errors"], f"{name}: {r['errors']}"
        assert r["kind"] == "onboarding", f"{name}: kind is {r['kind']!r}"
        assert r["emails"] >= 1


def test_main_sequence_covers_the_default_jobs():
    ek = load_emailkit()
    main = max((t for _, t in draft_blocks()), key=len)
    _, emails, _ = ek.parse(main)
    assert len(emails) == 8
    sends = [e["fields"]["send"] for e in emails]
    assert all(re.match(r"^(Day \d+|on \S)", s) for s in sends), sends
    assert sends[0].startswith("on contract signed")


def test_reminders_stop_at_two():
    ek = load_emailkit()
    reminders = [t for _, t in draft_blocks() if "reminder" in t.lower().split("---")[1]]
    assert reminders, "no reminders example found"
    for t in reminders:
        _, emails, _ = ek.parse(t)
        assert len(emails) <= 2


def test_examples_never_ask_for_a_password():
    for name, text in draft_blocks():
        for line in text.lower().splitlines():
            if "password" in line:
                assert re.search(r"\b(never|none|don't|do not|not)\b", line), f"{name}: {line.strip()}"


def test_no_em_or_en_dashes_anywhere_in_the_skill():
    for p in skill_files():
        text = p.read_text(encoding="utf-8")
        assert not DASHES.search(text), f"em or en dash in {p.relative_to(SKILL)}"


def test_no_absolute_user_paths():
    for p in skill_files():
        text = p.read_text(encoding="utf-8")
        assert not ABS_PATH.search(text), f"absolute path in {p.relative_to(SKILL)}"
