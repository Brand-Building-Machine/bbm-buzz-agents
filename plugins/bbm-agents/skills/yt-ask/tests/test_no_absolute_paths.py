import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
BAD = re.compile(r"(/Users/|/home/|C:\\\\)")


def test_no_absolute_or_home_paths():
    offenders = []
    for p in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.json")):
        if p == Path(__file__):
            continue
        if any(part in {".venv", "__pycache__", ".pytest_cache"} for part in p.parts):
            continue
        for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if BAD.search(line):
                offenders.append(f"{p}:{n}: {line.strip()}")
    assert not offenders, "absolute/home paths found:\n" + "\n".join(offenders)
