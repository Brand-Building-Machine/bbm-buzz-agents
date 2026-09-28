"""Location helpers for the YouTube research skills. No absolute paths baked in.

These skills ship inside a plugin that is installed into a plugin cache
directory, NOT inside the owner's workspace, and they can be launched from any
working directory on macOS, Linux or Windows. So nothing here walks up from
this file looking for a workspace, and nothing depends on the current working
directory.

Scratch output (fetched transcripts, bulk corpora without a --run-dir) goes to
one per-user data directory:

  1. $YT_SKILLS_DATA_DIR, if set (point it inside the owner's workspace if you
     want the files kept there), else
  2. the OS per-user cache directory:
       Windows  %LOCALAPPDATA%\\yt-skills
       macOS    ~/Library/Caches/yt-skills
       Linux    $XDG_CACHE_HOME/yt-skills  (default ~/.cache/yt-skills)
"""
import os
import sys
from pathlib import Path

DATA_DIR_ENV = "YT_SKILLS_DATA_DIR"


def skill_dir() -> Path:
    """This skill's own directory (the one holding SKILL.md)."""
    return Path(__file__).resolve().parents[1]


def skills_root() -> Path:
    """The directory holding all sibling skills of this plugin."""
    return skill_dir().parent


def data_root() -> Path:
    env = os.environ.get(DATA_DIR_ENV)
    if env:
        root = Path(env).expanduser()
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        root = Path(base) / "yt-skills"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Caches" / "yt-skills"
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        root = Path(base) / "yt-skills"
    root.mkdir(parents=True, exist_ok=True)
    return root


def tmp_dir() -> Path:
    """Where fetch.py writes {video_id}.json."""
    d = data_root() / "yt-intel"
    d.mkdir(parents=True, exist_ok=True)
    return d
