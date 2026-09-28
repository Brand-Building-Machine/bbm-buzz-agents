import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPT = SKILL / "scripts" / "emailkit.py"
spec = importlib.util.spec_from_file_location("emailkit", SCRIPT)
ek = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ek)

GOOD = """---
kind: no-show
business: Test Co
audience: A lead who missed a call
trigger: Missed a booked call
goal: Rebook the call
exit: Any reply
status: draft
---
# No-show

## Email 1: Easy reschedule
Send: Day 0
Subject: Missed you today
Preview: No problem, here are two times
CTA: Pick a time

Looks like today didn't work out, no problem at all.

Would Tuesday at 10 or Wednesday at 2 suit you better? Or pick any time here: [calendar](https://example.com).

Sam

## Email 2: Something useful
Send: Day 3
Subject: The question most people ask first
CTA: Reply with a time

Body with enough words to be a real email about the thing we would have covered.

Sam
"""


def run(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env)


def test_good_draft_passes():
    r = ek.check_text(GOOD)
    assert r["errors"] == [], r["errors"]
    assert r["emails"] == 2


def test_missing_frontmatter_and_fields():
    r = ek.check_text("# Nothing\n\n## Email 1: x\nSend: Day 0\n\nhello\n")
    assert any("no frontmatter" in e for e in r["errors"])
    assert any("Subject" in e for e in r["errors"])
    assert any("CTA" in e for e in r["errors"])


def test_dashes_banned_phrases_slots_emoji():
    bad = GOOD.replace("no problem at all.", "no problem — just checking in {{NAME}} \U0001F600")
    errs = " | ".join(ek.check_text(bad)["errors"])
    assert "dash" in errs and "just checking in" in errs and "SLOT" in errs and "emoji" in errs


def test_curly_apostrophe_banned_phrase_caught():
    bad = GOOD.replace("Looks like", "I hope you’re doing well. Looks like")
    assert any("doing well" in e for e in ek.check_text(bad)["errors"])


def test_emoji_allowed_by_frontmatter():
    ok = GOOD.replace("status: draft", "status: draft\nemoji: allowed").replace("no problem at all.", "no problem \U0001F600")
    assert ek.check_text(ok)["errors"] == []


def test_pacing_and_touch_cap():
    too_close = GOOD.replace("Send: Day 3", "Send: Day 1")
    assert any("under 2 days" in e for e in ek.check_text(too_close)["errors"])
    blocks = "".join(f"\n## Email {i}: t\nSend: Day {i * 3}\nSubject: s{i}\nCTA: reply\n\nshort body here\n" for i in range(1, 7))
    many = GOOD.split("# No-show")[0] + "# x\n" + blocks
    assert any("stop at 5" in e for e in ek.check_text(many)["errors"])


def test_pacing_not_applied_to_marketing_sequences():
    daily = GOOD.replace("kind: no-show", "kind: course").replace("Send: Day 3", "Send: Day 1")
    assert not any("days after" in e for e in ek.check_text(daily)["errors"])


def test_word_limits():
    long_body = " ".join(["word"] * 240)
    r = ek.check_text(GOOD.replace("Body with enough words", long_body))
    assert any("hard limit" in e for e in r["errors"])
    r = ek.check_text(GOOD.replace("Body with enough words", " ".join(["word"] * 170)))
    assert not r["errors"] and any("target" in w for w in r["warnings"])


def test_cold_rules():
    cold = GOOD.replace("kind: no-show", "kind: cold")
    errs = " | ".join(ek.check_text(cold)["errors"])
    assert "link" in errs
    fake = cold.replace("Subject: Missed you today", "Subject: Re: our chat")
    assert any("fakes a reply" in e for e in ek.check_text(fake)["errors"])


def test_warnings_for_claims_subjects_and_tbd():
    w = GOOD.replace("Subject: Missed you today", "Subject: HUGE news: this is a very long subject line that goes on and on and on!")
    w = w.replace("Body with", "We cut costs 40% for [Client to provide: client]. Body with")
    warns = " | ".join(ek.check_text(w)["warnings"])
    assert "characters" in warns and "exclamation" in warns and "ALL CAPS" in warns
    assert "40%" in warns and "Client to provide" in warns


def test_numbering_and_exit():
    r = ek.check_text(GOOD.replace("## Email 2", "## Email 3"))
    assert any("numbered" in e for e in r["errors"])
    r = ek.check_text(GOOD.replace("exit: Any reply\n", ""))
    assert any("exit" in e for e in r["errors"])


def test_unknown_kind():
    assert any("unknown kind" in e for e in ek.check_text(GOOD.replace("no-show", "newsletterz"))["errors"])


def test_examples_in_references_pass():
    for ref in (SKILL / "references").glob("*.md"):
        text = ref.read_text(encoding="utf-8")
        for block in re.findall(r"```markdown\n(.*?)```", text, re.S):
            if block.startswith("---"):
                r = ek.check_text(block)
                assert r["errors"] == [], (ref.name, r["errors"])


def test_no_dashes_in_skill_files():
    for p in SKILL.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".py"} and p.name != "test_emailkit.py":
            assert not re.search("[—–]", p.read_text(encoding="utf-8")), p


def test_cli_check_and_paths_and_voice(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text(GOOD, encoding="utf-8")
    r = run("check", str(draft), "--json")
    assert r.returncode == 0 and json.loads(r.stdout)[str(draft)]["errors"] == []
    draft.write_text(GOOD.replace("Missed you today", "Re: Missed you").replace("no-show", "cold"), encoding="utf-8")
    assert run("check", str(draft)).returncode == 1

    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"PROPOSED_PATH": str(tmp_path / "proposed"),
                               "BRAND_PATH": str(tmp_path / "brand" / "{business}")}), encoding="utf-8")
    env = {**os.environ, "BUZZ_AGENTS_CONFIG": str(cfg)}
    r = run("paths", "--business", "acme", env=env)
    assert r.returncode == 0 and "email" in r.stdout and "brand-bible" in r.stdout
    assert run("paths", env=env).returncode == 2
    r = run("voice", "init", "--business", "acme", env=env)
    voice = tmp_path / "brand" / "acme" / "email-voice.md"
    assert r.returncode == 0 and voice.exists() and "{{DATE}}" not in voice.read_text(encoding="utf-8")
    voice.write_text("owner edits", encoding="utf-8")
    run("voice", "init", "--business", "acme", env=env)
    assert voice.read_text(encoding="utf-8") == "owner edits"


def test_no_config_fails_loudly(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "BUZZ_AGENTS_CONFIG"}
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    r = subprocess.run([sys.executable, str(SCRIPT), "paths"], capture_output=True, text=True, cwd=tmp_path, env=env)
    assert r.returncode == 2 and "workspace-config" in r.stderr


def test_blank_line_inside_fields_and_placeholder_words():
    spaced = GOOD.replace("Preview: No problem, here are two times\n", "\nPreview: No problem, here are two times\n")
    assert ek.check_text(spaced)["errors"] == []
    tbd = "[Client to provide: " + " ".join(["word"] * 300) + "]"
    assert not any("hard limit" in e for e in ek.check_text(GOOD.replace("Body with", tbd))["errors"])


def test_header_dash_money_claim_and_send_format():
    r = ek.check_text(GOOD.replace("goal: Rebook the call", "goal: Rebook — fast"))
    assert any("frontmatter or title" in e for e in r["errors"])
    r = ek.check_text(GOOD.replace("Body with", "Saved $12,000 last year. Body with").replace("Send: Day 3", "Send: whenever"))
    warns = " | ".join(r["warnings"])
    assert "$12,000" in warns and "Day N" in warns


def test_cold_links_in_fields_bare_domains_and_opt_out():
    cold = GOOD.replace("kind: no-show", "kind: cold").replace(
        "Or pick any time here: [calendar](https://example.com).", "Not relevant? Say so and I won't email again.")
    assert not any("link" in e for e in ek.check_text(cold)["errors"])
    assert any("opt-out" in w for w in ek.check_text(cold)["warnings"])  # email 2 has none
    assert any("link" in e for e in ek.check_text(cold.replace("Preview: No problem", "Preview: see https://x.io"))["errors"])
    assert any("link" in e for e in ek.check_text(cold.replace("Looks like", "Visit acme.com/book. Looks like"))["errors"])
    assert any("fakes" in e for e in ek.check_text(GOOD.replace("Subject: The question", "Subject: Re: The question"))["errors"])


def test_prospect_tables_are_skipped(tmp_path):
    table = tmp_path / "2026-01-01-cold-x-prospects.md"
    table.write_text("| Prospect | Hook |\n|---|---|\n", encoding="utf-8")
    r = run("check", str(table))
    assert r.returncode == 0 and "SKIP" in r.stdout
