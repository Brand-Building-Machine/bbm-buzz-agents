"""Location helpers for yt-ask. Resolved from this file, never from cwd.

yt-ask owns no fetching logic; it loads the sibling yt-intel skill's fetch.py.
Both skills are installed side by side in the same plugin `skills/` folder, so
the sibling is found relative to this file wherever the plugin is installed.
"""
from pathlib import Path


def skill_dir() -> Path:
    """This skill's own directory (the one holding SKILL.md)."""
    return Path(__file__).resolve().parents[1]


def yt_intel_dir() -> Path:
    d = skill_dir().parent / "yt-intel"
    if not (d / "scripts" / "fetch.py").is_file():
        raise RuntimeError(
            f"yt-ask needs the sibling yt-intel skill next to it; expected {d / 'scripts' / 'fetch.py'}"
        )
    return d
