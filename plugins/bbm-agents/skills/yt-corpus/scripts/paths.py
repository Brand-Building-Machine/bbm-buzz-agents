"""Location helpers for yt-corpus. Resolved from this file, never from cwd.

yt-corpus reuses the sibling yt-intel skill's caption path (fetch.py) instead
of duplicating it. Both skills are installed side by side in the same plugin
`skills/` folder, so the sibling is found relative to this file wherever the
plugin is installed. The per-user data directory is yt-intel's (see
yt-intel/scripts/paths.py), so all the YouTube skills share one location.
"""
from pathlib import Path


def skill_dir() -> Path:
    """This skill's own directory (the one holding SKILL.md)."""
    return Path(__file__).resolve().parents[1]


def yt_intel_dir() -> Path:
    d = skill_dir().parent / "yt-intel"
    if not (d / "scripts" / "fetch.py").is_file():
        raise RuntimeError(
            f"yt-corpus needs the sibling yt-intel skill next to it; expected {d / 'scripts' / 'fetch.py'}"
        )
    return d


def default_corpus_dir(slug: str, data_root: Path) -> Path:
    """Fallback when no --run-dir is given: <data root>/yt-corpus/<slug>.
    Scratch by design -- pass --run-dir to put a corpus somewhere durable."""
    d = data_root / "yt-corpus" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d
