"""Offline tests for linkedin.py. Run from outside the skill dir:
    python3 -m pytest <abs path>/tests -q -p no:cacheprovider
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import linkedin  # noqa: E402

LI = SCRIPTS / "linkedin.py"

CLEAN_POST = """$11,240. That's what one misquoted renewal cost a client of ours last spring.

The carrier changed the plan design in March and nobody read page 14.

We caught it in June, three months after the premiums went out.

Now every renewal gets a second read by someone who didn't build the quote.

What's the one document in your business nobody reads twice?"""


def write(tmp, name, text):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    brand = tmp_path / "canon" / "brand"
    brand.mkdir(parents=True)
    cfg = {"OWNER_NAME": "Sam", "PROPOSED_PATH": str(tmp_path / "proposed"), "BRAND_PATH": str(brand),
           "WORKSPACE_MAP": str(tmp_path / "AGENTS.md")}
    cfg_path = tmp_path / "buzz-agents.config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("BUZZ_AGENTS_CONFIG", str(cfg_path))
    return tmp_path, brand, cfg_path


def run(*args, env=None):
    return subprocess.run([sys.executable, str(LI), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, encoding="utf-8")


# ---------- post lint ----------

def test_clean_post_has_no_errors_or_warnings():
    errors, warnings, stats = linkedin.lint_text(CLEAN_POST)
    assert errors == []
    assert warnings == []
    assert stats["chars"] == len(CLEAN_POST)


def test_em_dash_is_an_error():
    errors, _, _ = linkedin.lint_text("We grew 40% — in one quarter.\n\nThat was March.")
    assert any("em dash" in e for e in errors)


def test_model_leakage_is_an_error():
    errors, _, _ = linkedin.lint_text("As of my last update, renewals rose.")
    assert any("leakage" in e for e in errors)


def test_over_limit_is_an_error():
    errors, _, _ = linkedin.lint_text("word " * 700)
    assert any("3000" in e for e in errors)


def test_question_opener_and_long_first_line_warn():
    _, warnings, _ = linkedin.lint_text("Why do renewals go wrong?\n\nBecause nobody reads them.")
    assert any("opens with a question" in w for w in warnings)
    _, warnings, _ = linkedin.lint_text("x" * 200 + "\n\nmore")
    assert any("first line" in w for w in warnings)


@pytest.mark.parametrize("text,needle", [
    ("We fixed it.\n\nThe result? Fewer calls.", "reveal"),
    ("Let me be honest, it hurt.", "sincerity"),
    ("It's not the price, it's the service. It's not the carrier, it's the broker.", "contrasts"),
    ("Here's what I learned from 10 years.", "stock opener"),
    ("Great week.\n\nWhat do you think?", "engagement bait"),
    ("Read it here https://example.com/post", "link"),
    ("Big news #a #b #c #d", "hashtags"),
    ("It cost [Client to provide] in March.", "placeholder"),
    ("Simple. Fast. Done. That's it.", "fragments"),
])
def test_warnings(text, needle):
    _, warnings, _ = linkedin.lint_text(text)
    assert any(needle in w for w in warnings), warnings


def test_vocab_density_is_per_paragraph():
    one_each = "We leverage data.\n\nIt was crucial.\n\nA robust plan."
    _, warnings, _ = linkedin.lint_text(one_each)
    assert not any("AI-tell" in w for w in warnings)
    dense = "We leverage robust insights to streamline the landscape."
    _, warnings, _ = linkedin.lint_text(dense)
    assert any("AI-tell" in w for w in warnings)


def test_post_sections_read_every_version():
    md = "# LinkedIn post: x\n\n## Post A\nFirst version.\n\n## Post B\nSecond — version.\n\n## First comment\nhttps://x.com\n"
    secs = linkedin.post_sections(md)
    assert [t for t, _ in secs] == ["Post A", "Post B"]


def test_lint_cli_markdown(tmp_path):
    ok = write(tmp_path, "post.md", "## Post A\n" + CLEAN_POST + "\n\n## First comment\nhttps://example.com\n")
    r = run("lint", ok)
    assert r.returncode == 0, r.stdout + r.stderr
    bad = write(tmp_path, "bad.md", "## Post A\nOne — two.\n")
    r = run("lint", bad, "--json")
    assert r.returncode == 1
    assert json.loads(r.stdout)["ok"] is False


# ---------- slides lint ----------

def slides(n_points=3, cover="3 renewal mistakes that cost you", route="html"):
    s = [{"n": 1, "role": "cover", "headline": cover, "body": ""}]
    s += [{"n": i + 2, "role": "point", "headline": f"Mistake {i + 1}", "body": "One short line."}
          for i in range(n_points)]
    s.append({"n": n_points + 2, "role": "close", "headline": "Save this", "body": "Follow for more."})
    return {"route": route, "slides": s}


def test_good_slides_pass():
    errors, warnings, stats = linkedin.lint_slides(slides())
    assert errors == []
    assert warnings == []
    assert stats["slides"] == 5


def test_cover_count_must_match_points():
    _, warnings, _ = linkedin.lint_slides(slides(n_points=4))
    assert any("promises 3" in w for w in warnings)


def test_slide_limits():
    d = slides()
    d["slides"][1]["body"] = "word " * 40
    d["slides"][2]["headline"] = "one two three four five six seven eight nine ten eleven"
    d["slides"][3]["headline"] = "Bad — dash"
    errors, warnings, _ = linkedin.lint_slides(d)
    assert any("em dash" in e for e in errors)
    assert any("words of body" in w for w in warnings)
    assert any("headline is 11 words" in w for w in warnings)


def test_image_route_wants_prompts_and_valid_route():
    _, warnings, _ = linkedin.lint_slides(slides(route="image"))
    assert any("image prompt" in w for w in warnings)
    errors, _, _ = linkedin.lint_slides(slides(route="canva"))
    assert any("route" in e for e in errors)


def test_slide_count_and_roles():
    d = {"route": "html", "slides": [{"role": "point", "headline": "a", "body": "b"}] * 2}
    _, warnings, _ = linkedin.lint_slides(d)
    assert any("usual range" in w for w in warnings)
    assert any("cover" in w for w in warnings)
    assert any("close" in w for w in warnings)


def test_lint_cli_json_checks_post_text_too(tmp_path):
    d = slides()
    d["post"] = "Great — carousel."
    p = write(tmp_path, "slides.json", json.dumps(d))
    r = run("lint", p)
    assert r.returncode == 1
    assert "post text" in r.stdout


# ---------- config, paths, profile, stories, folders ----------

def test_paths_reports_missing_brand_files(workspace):
    tmp, brand, _ = workspace
    (brand / "voice-agent.md").write_text("x", encoding="utf-8")
    r = run("paths")
    assert r.returncode == 0
    info = json.loads(r.stdout)
    assert info["drafts"] == str(tmp / "proposed" / "linkedin")
    assert info["brand_files_present"] == ["voice-agent.md"]
    assert "brand-bible" in r.stderr
    assert Path(info["visuals_script"]).name == "visuals.py"
    assert Path(info["visuals_script"]).exists()


def test_per_business_paths_need_business(workspace):
    tmp, _, cfg_path = workspace
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["BRAND_PATH"] = str(tmp / "biz" / "{business}" / "brand")
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    assert run("paths").returncode == 2
    r = run("paths", "--business", "acme")
    assert json.loads(r.stdout)["drafts"].endswith(str(Path("linkedin") / "acme"))


def test_no_config_fails_loudly(tmp_path):
    r = subprocess.run([sys.executable, str(LI), "paths"], capture_output=True, text=True, cwd=tmp_path,
                       env={**os.environ, "BUZZ_AGENTS_CONFIG": str(tmp_path / "nope.json"),
                            "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)})
    assert r.returncode == 2
    assert "workspace-config" in r.stderr


def test_profile_init_check_and_never_overwrite(workspace):
    _, brand, _ = workspace
    assert run("profile", "check").returncode == 1
    assert run("profile", "init").returncode == 0
    r = run("profile", "check")
    assert r.returncode == 1 and "author" in r.stdout and "pillars" in r.stdout
    prof = json.loads((brand / "linkedin.json").read_text(encoding="utf-8"))
    prof.update({"author": "Sam Lee", "audience": "Owners of 20-200 person companies",
                 "pillars": ["renewals", "hiring"]})
    (brand / "linkedin.json").write_text(json.dumps(prof), encoding="utf-8")
    assert run("profile", "check").returncode == 0
    run("profile", "init")
    assert json.loads((brand / "linkedin.json").read_text(encoding="utf-8"))["author"] == "Sam Lee"


def test_profile_image_route_needs_provider():
    p = dict(linkedin.PROFILE_TEMPLATE, author="a", audience="b", pillars=["x", "y"])
    p["visuals"] = {"default": "hybrid", "provider": "", "size": "1080x1350"}
    assert any("provider" in x for x in linkedin.profile_problems(p))
    p["visuals"]["provider"] = "higgsfield"
    assert linkedin.profile_problems(p) == []


def test_stories_init_never_overwrites(workspace):
    _, brand, _ = workspace
    assert run("stories", "init").returncode == 0
    f = brand / "linkedin-stories.md"
    assert "Sam" in f.read_text(encoding="utf-8")
    f.write_text("mine", encoding="utf-8")
    run("stories", "init")
    assert f.read_text(encoding="utf-8") == "mine"


def test_new_makes_dated_unique_folders(workspace):
    tmp, _, _ = workspace
    a = Path(run("new", "carousel", "--slug", "5 Renewal Mistakes!").stdout.strip())
    b = Path(run("new", "carousel", "--slug", "5 Renewal Mistakes!").stdout.strip())
    today = dt.date.today().isoformat()
    assert a.name == f"{today}-carousel-5-renewal-mistakes"
    assert b.name == a.name + "-2"
    assert a.is_dir() and b.is_dir()
    assert a.parent == tmp / "proposed" / "linkedin"
