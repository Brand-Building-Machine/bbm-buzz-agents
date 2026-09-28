"""Portability: paths resolve from this skill's own file, never from cwd or a workspace."""
import os
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
from scripts import fetch  # noqa: E402


def test_skill_dir_is_this_skill(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # cwd must not matter
    assert fetch.paths.skill_dir() == SKILL
    assert (fetch.paths.skills_root() / "yt-intel" / "SKILL.md").is_file()


def test_data_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("YT_SKILLS_DATA_DIR", str(tmp_path / "data"))
    assert fetch.paths.tmp_dir() == tmp_path / "data" / "yt-intel"
    assert (tmp_path / "data" / "yt-intel").is_dir()


def test_data_dir_default_is_per_user_not_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("YT_SKILLS_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.chdir(tmp_path)
    root = fetch.paths.data_root()
    assert root.name == "yt-skills"
    assert root != Path.cwd()


def test_load_key_from_env_only(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "owner-key")
    assert fetch._load_key() == "owner-key"


def test_load_key_none_without_env_or_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # empty dir, no .env
    assert fetch._load_key() is None


def test_load_key_reads_explicit_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    envf = tmp_path / ".env"
    envf.write_text('export GEMINI_API_KEY="from-file"\n', encoding="utf-8")
    assert fetch._load_key(env_path=envf) == "from-file"
