"""Offline tests for wiki.py. Run: python3 -m pytest <this dir> -q"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wiki.py"


def run(cfg, *args):
    env = {"BUZZ_AGENTS_CONFIG": str(cfg), "PATH": "", "SYSTEMROOT": ""}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def make_ws(tmp_path):
    ws = tmp_path / "ws"
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({
        "WORKSPACE_ROOT": str(ws),
        "RAW_SOURCES_PATH": str(ws / "raw"),
        "WIKI_PATH": str(ws / "wiki"),
        "STATE_PATH": str(ws / "state"),
    }), encoding="utf-8")
    return ws, cfg


def test_missing_config_exits_2(tmp_path):
    assert run(tmp_path / "nope.json", "paths").returncode == 2


def test_missing_keys_exits_2(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"WORKSPACE_ROOT": str(tmp_path)}), encoding="utf-8")
    r = run(cfg, "paths")
    assert r.returncode == 2 and "WIKI_PATH" in r.stderr


def test_init_is_idempotent_and_never_overwrites(tmp_path):
    ws, cfg = make_ws(tmp_path)
    assert run(cfg, "init").returncode == 0
    for sub in ("wiki/entities", "wiki/concepts", "wiki/topics", "raw", "state"):
        assert (ws / sub).is_dir()
    (ws / "wiki" / "index.md").write_text("MINE", encoding="utf-8")
    r = run(cfg, "init")
    assert "nothing to create" in r.stdout
    assert (ws / "wiki" / "index.md").read_text(encoding="utf-8") == "MINE"


def test_unprocessed_lists_only_waiting_sources(tmp_path):
    ws, cfg = make_ws(tmp_path)
    run(cfg, "init")
    (ws / "raw" / "a.md").write_text("---\nstatus: unprocessed\ndate_captured: 2026-01-02\n---\nx", encoding="utf-8")
    (ws / "raw" / "b.md").write_text("---\nstatus: processed\n---\nx", encoding="utf-8")
    (ws / "raw" / "c.md").write_text("---\nstatus: needs-review\ndate_captured: 2026-01-01\n---\nx", encoding="utf-8")
    out = run(cfg, "unprocessed").stdout
    assert "a.md" in out and "c.md" in out and "b.md" not in out
    assert out.index("c.md") < out.index("a.md")  # oldest first


def test_lint_finds_each_structural_problem(tmp_path):
    ws, cfg = make_ws(tmp_path)
    run(cfg, "init")
    w = ws / "wiki"
    (w / "entities" / "Acme.md").write_text(
        "---\ntitle: Acme\nid: ENT-acme\nrelated: [ENT-ghost, ENT-acme]\n---\n"
        "[[Widget]] [[Nope|x]] `[[InlineCode]]` [[ENT-acme]]\n```\n[[InFence]]\n```\n", encoding="utf-8")
    (w / "concepts" / "Widget.md").write_text("---\ntitle: Widget\n---\n", encoding="utf-8")
    (w / "topics" / "Lonely Page.md").write_text("---\ntitle: Lonely Page\n---\n", encoding="utf-8")
    (w / "index.md").write_text("[[Acme]]", encoding="utf-8")
    (ws / "raw" / "old.md").write_text("---\nstatus: unprocessed\ndate_captured: 2020-01-01\n---\n", encoding="utf-8")
    d = json.loads(run(cfg, "lint", "--json").stdout)
    assert [Path(p).name for p in d["orphans"]] == ["Lonely Page.md"]
    assert len(d["stale_sources"]) == 1 and "old.md" in d["stale_sources"][0]
    assert d["broken_related"] and "ENT-ghost" in d["broken_related"][0]
    assert d["dead_links"] == [f"{w / 'entities' / 'Acme.md'} -> [[Nope]]"]


def test_unicode_titles_do_not_crash(tmp_path):
    ws, cfg = make_ws(tmp_path)
    run(cfg, "init")
    (ws / "wiki" / "topics" / "Café — Ünïcode.md").write_text("---\ntitle: Café\n---\n→ 🚀", encoding="utf-8")
    assert run(cfg, "lint").returncode == 0
