"""yt-ask must find the sibling yt-intel skill from its own file location, not the cwd."""
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
from scripts import ask  # noqa: E402


def test_yt_intel_resolved_as_sibling():
    assert ask.paths.yt_intel_dir() == SKILL.parent / "yt-intel"


def test_loaded_fetch_is_yt_intels_and_uses_its_own_paths():
    # Regression: fetch.py used to `from scripts import paths`, which inside yt-ask
    # resolved to yt-ask's paths module (no tmp_dir) and broke the audio fallback.
    assert Path(ask.ytfetch.__file__).resolve() == SKILL.parent / "yt-intel" / "scripts" / "fetch.py"
    assert hasattr(ask.ytfetch.paths, "tmp_dir")
    assert ask.ytfetch.paths.skill_dir() == SKILL.parent / "yt-intel"
