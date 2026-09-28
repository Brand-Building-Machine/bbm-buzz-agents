"""Offline tests for email-cold-outbound. Run: python3 -m pytest <this dir> -q"""
import importlib.util
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
EMAILKIT = SKILL.parent / "email-sequences" / "scripts" / "emailkit.py"
DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
FENCE = re.compile(r"```markdown\n(.*?)```", re.S)


def load_emailkit():
    spec = importlib.util.spec_from_file_location("emailkit", EMAILKIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def examples():
    found = []
    for f in sorted((SKILL / "references").glob("*.md")):
        for block in FENCE.findall(f.read_text(encoding="utf-8")):
            if block.startswith("---"):
                found.append((f.name, block))
    return found


def test_there_is_a_full_example():
    ex = examples()
    assert ex, "no ```markdown draft example found in references/"
    kit = load_emailkit()
    assert any(kit.check_text(b)["kind"] == "cold" and kit.check_text(b)["emails"] >= 3 for _, b in ex)


def test_examples_pass_the_checker():
    kit = load_emailkit()
    for name, block in examples():
        result = kit.check_text(block)
        assert not result["errors"], f"{name}: {result['errors']}"


def test_no_em_or_en_dashes_anywhere():
    for f in SKILL.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".py"}:
            text = f.read_text(encoding="utf-8")
            assert not DASHES.search(text), f"dash in {f.relative_to(SKILL)}"
