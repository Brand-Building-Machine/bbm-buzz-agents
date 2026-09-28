#!/usr/bin/env python3
"""Email drafting helper for the email skills. Stdlib only; macOS, Linux, Windows.

Deterministic checks only. Writing and judgement are the agent's job. Nothing here sends email.

  emailkit.py paths [--business NAME]          # drafts folder, brand + voice files present
  emailkit.py voice init [--business NAME]     # create email-voice.md in the brand folder (never overwrites)
  emailkit.py check FILE [FILE ...] [--json]   # lint drafts written in references/draft-format.md

Exit codes: 0 ok, 1 check failed, 2 config or usage problem.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

POINTER = Path.home() / ".bbm-agents.json"
CONFIG_NAME = "buzz-agents.config.json"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
BRAND_FILES = ["brand-bible.md", "voice-agent.md", "offers.md"]
VOICE_FILE = "email-voice.md"

# kind -> (target words, hard limit, minimum words)
SEQUENCE_KINDS = {"lead-magnet", "welcome", "nurture", "sales", "course", "reengagement"}
FOLLOWUP_KINDS = {"call-recap", "no-show", "proposal", "gone-quiet", "breakup", "reply", "one-off"}
LIMITS = {k: (350, 500, 50) for k in SEQUENCE_KINDS}
LIMITS.update({k: (150, 220, 0) for k in FOLLOWUP_KINDS})
LIMITS["call-recap"] = (250, 350, 0)
LIMITS["onboarding"] = (300, 450, 0)
LIMITS["cold"] = (90, 125, 30)
# Sequences where every touch interrupts someone who hasn't asked: pace and cap them.
PACED_KINDS = FOLLOWUP_KINDS | {"cold"}
MAX_TOUCHES = 5
MIN_GAP_DAYS = 2

FRONT_REQUIRED = ["kind", "business", "audience", "trigger", "goal", "status"]
BANNED = [
    "i hope this email finds you well", "i hope this finds you well", "i hope you're doing well",
    "i hope you are doing well", "just checking in", "just following up", "just circling back",
    "circling back", "touching base", "i wanted to reach out", "bumping this", "did you get a chance to",
    "per my last email", "as per my previous email", "i never heard back", "don't hesitate to",
    "do not hesitate to", "at your earliest convenience", "pick your brain", "game-changer",
    "game changer", "unlock your potential", "take it to the next level", "fast-paced world", "delve",
    "synergy", "leverage your", "leverage our", "did you see my last email", "any update on",
    "following up on my previous", "following up on my last", "i guess you're busy",
]
DASHES = re.compile("[\u2014\u2013]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002B50\U00002764\U0001F000-\U0001F2FF]")
SLOT = re.compile(r"\{\{[^}]*\}\}")
LINK = re.compile(r"\[[^\]]+\]\([^)]+\)|https?://\S+")
CLAIM = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|percent\b|x\b|times\b)", re.I)
TBD = re.compile(r"\[Client to provide[^\]]*\]", re.I)
DAY = re.compile(r"\bday\s*(\d+)", re.I)
BARE = re.compile(r"\b[a-z0-9-]+\.(?:com|co|net|org|io|ca|uk|au|us|biz)(?:/\S*)?\b", re.I)
OPT_OUT = re.compile(r"unsubscribe|opt out|won't email|not email you|stop emailing|not relevant|no more emails|let me know if not", re.I)
FIELD = re.compile(r"^(Send|Subject|Alt subject|Preview|CTA)\s*:\s*(.*)$", re.I)
MONEY = re.compile(r"[$\u00a3\u20ac]\s?\d[\d,.]*\s?[kKmM]?")


def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def load_config():
    env = os.environ.get("BUZZ_AGENTS_CONFIG")
    path = Path(env).expanduser() if env else None
    if not path and POINTER.exists():
        try:
            path = Path(json.loads(POINTER.read_text(encoding="utf-8"))["config"]).expanduser()
        except (ValueError, KeyError):
            path = None
    if not path:
        for d in [Path.cwd(), *Path.cwd().parents]:
            if (d / CONFIG_NAME).exists():
                path = d / CONFIG_NAME
                break
    if not path or not path.exists():
        die("No buzz-agents config found. Run the workspace-config skill first.")
    return json.loads(path.read_text(encoding="utf-8"))


def brand_dir(cfg, business):
    pattern = cfg.get("BRAND_PATH")
    if not pattern:
        return None
    if "{business}" in pattern:
        if not business:
            die("This workspace has one brand per business. Pass --business <name>.")
        return Path(pattern.replace("{business}", business)).expanduser()
    return Path(pattern).expanduser()


def drafts_dir(cfg):
    base = cfg.get("PROPOSED_PATH")
    if not base:
        die("Config has no PROPOSED_PATH. Run workspace-config to add where drafts go.")
    return Path(base).expanduser() / "email"


# ---------- commands ----------

def cmd_paths(a):
    cfg = load_config()
    print(f"drafts folder: {drafts_dir(cfg)}")
    b = brand_dir(cfg, a.business)
    if not b:
        print("brand folder: not configured (no BRAND_PATH). Run workspace-config, then brand-bible.")
        return
    print(f"brand folder: {b} ({'exists' if b.exists() else 'missing'})")
    for f in BRAND_FILES + [VOICE_FILE]:
        state = "present" if (b / f).exists() else "MISSING"
        print(f"  {f:18} {state}")
    if not (b / "brand-bible.md").exists():
        print("next: run brand-bible before writing emails")
    elif not (b / VOICE_FILE).exists():
        print("next: build the email voice (emailkit.py voice init, then references/voice.md)")


def cmd_voice(a):
    cfg = load_config()
    b = brand_dir(cfg, a.business)
    if not b:
        die("Config has no BRAND_PATH. Run workspace-config first.")
    b.mkdir(parents=True, exist_ok=True)
    target = b / VOICE_FILE
    if target.exists():
        print(f"already there, left untouched: {target}")
        return
    text = (TEMPLATES / VOICE_FILE).read_text(encoding="utf-8")
    target.write_text(text.replace("{{DATE}}", dt.date.today().isoformat()), encoding="utf-8")
    print(f"created: {target}")


def parse(text):
    """Return (frontmatter dict, [email dicts], problems)."""
    problems = []
    front = {}
    text = text.lstrip("\ufeff")
    rest = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end == -1:
            problems.append("frontmatter is not closed with ---")
        else:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    front[k.strip().lower()] = v.strip()
            rest = text[end + 4:]
    else:
        problems.append("no frontmatter (the file must start with ---)")
    emails = []
    parts = re.split(r"^##\s+Email\s+(\d+)\s*:?\s*(.*)$", rest, flags=re.M | re.I)
    for i in range(1, len(parts), 3):
        num, title, block = int(parts[i]), parts[i + 1].strip(), parts[i + 2]
        fields, body_lines, in_body = {}, [], False
        lines = block.strip("\n").splitlines()
        for j, line in enumerate(lines):
            m = FIELD.match(line)
            if not in_body and m:
                fields[m.group(1).lower()] = m.group(2).strip()
            elif not in_body and not line.strip():
                # A blank line ends the field block unless another field line follows it.
                nxt = next((x for x in lines[j + 1:] if x.strip()), "")
                in_body = bool(fields) and not FIELD.match(nxt)
            else:
                in_body = True
                body_lines.append(line)
        emails.append({"num": num, "title": title, "fields": fields, "body": "\n".join(body_lines).strip()})
    return front, emails, problems


def words(s):
    return len(re.findall(r"[A-Za-z0-9'][A-Za-z0-9'\-]*", TBD.sub("x", LINK.sub("link", s))))


def check_text(text):
    errors, warnings = [], []
    front, emails, problems = parse(text)
    errors += problems
    kind = front.get("kind", "").lower()
    for k in FRONT_REQUIRED:
        if not front.get(k):
            errors.append(f"frontmatter: missing '{k}'")
    if kind and kind not in LIMITS:
        errors.append(f"frontmatter: unknown kind '{kind}' (see draft-format.md)")
    if front.get("status", "draft").lower() != "draft":
        warnings.append("status is not 'draft': only the owner changes that")
    if not emails:
        errors.append("no emails found (each starts with '## Email N: <job>')")
    if len(emails) > 1 and not front.get("exit"):
        errors.append("frontmatter: missing 'exit' (what stops the sequence early)")
    emoji_ok = front.get("emoji", "").lower() == "allowed"
    head = "\n".join([*front.values(), *re.findall(r"^#\s+.*$", text, re.M)])
    if DASHES.search(head):
        errors.append("frontmatter or title: em or en dash")
    if SLOT.search(head):
        errors.append("frontmatter or title: unfilled {{SLOT}}")
    target, hard, minimum = LIMITS.get(kind, (350, 500, 0))

    nums = [e["num"] for e in emails]
    if nums and nums != list(range(1, len(nums) + 1)):
        errors.append(f"emails must be numbered 1..{len(nums)} in order (found {nums})")
    if kind in PACED_KINDS and len(emails) > MAX_TOUCHES:
        errors.append(f"{len(emails)} touches: {kind} sequences stop at {MAX_TOUCHES}")

    prev_day = None
    for e in emails:
        tag = f"email {e['num']}"
        f, body = e["fields"], e["body"]
        for req in ("send", "subject", "cta"):
            if not f.get(req):
                errors.append(f"{tag}: missing '{ {'send': 'Send', 'subject': 'Subject', 'cta': 'CTA'}[req] }:' line")
        if not body:
            errors.append(f"{tag}: no body")
        subj = f.get("subject", "")
        for label, s in (("subject", subj), ("alt subject", f.get("alt subject", ""))):
            if not s:
                continue
            if len(s) > 60:
                warnings.append(f"{tag}: {label} is {len(s)} characters (keep under about 50)")
            if "!" in s:
                warnings.append(f"{tag}: {label} has an exclamation mark")
            if any(len(w) > 3 and w.isupper() and w.isalpha() for w in s.split()):
                warnings.append(f"{tag}: {label} has an ALL CAPS word")
            if re.match(r"^\s*(re|fwd?)\s*:", s, re.I) and kind != "reply":
                errors.append(f"{tag}: {label} fakes a reply/forward ('Re:'/'Fwd:')")
        whole = "\n".join([e["title"], *f.values(), body])
        low = re.sub(r"[\u2018\u2019]", "'", whole.lower())
        if DASHES.search(whole):
            errors.append(f"{tag}: em or en dash (use a comma, full stop, colon or brackets)")
        if SLOT.search(whole):
            errors.append(f"{tag}: unfilled {{{{SLOT}}}}")
        for p in BANNED:
            if p in low:
                errors.append(f"{tag}: banned phrase '{p}'")
        if not emoji_ok and EMOJI.search(whole):
            errors.append(f"{tag}: emoji (set 'emoji: allowed' only if the owner's voice uses them)")
        n = words(body)
        if n > hard:
            errors.append(f"{tag}: {n} words, hard limit for {kind or 'this kind'} is {hard}")
        elif n > target:
            warnings.append(f"{tag}: {n} words, target for {kind or 'this kind'} is {target} or fewer")
        elif body and n < minimum:
            warnings.append(f"{tag}: only {n} words (usual minimum for {kind} is {minimum})")
        links = len(LINK.findall(body))
        if links > 2:
            warnings.append(f"{tag}: {links} links (one call to action; a second link only for the same action)")
        if kind == "cold":
            first_links = LINK.findall(" ".join([body, f.get("preview", ""), f.get("cta", "")])) + BARE.findall(body)
            if e["num"] == 1 and first_links:
                errors.append(f"{tag}: first cold email has a link (hurts delivery; ask for a reply instead)")
            if re.search(r"!\[[^\]]*\]\(", body):
                errors.append(f"{tag}: image in a cold email")
            if not OPT_OUT.search(body):
                warnings.append(f"{tag}: no opt-out line (cold email needs a clear way to say no, and a postal address)")
        for m in [*CLAIM.finditer(body), *MONEY.finditer(body)]:
            warnings.append(f"{tag}: '{m.group(0).strip()}' looks like a claim: confirm it is real and sourced")
        if TBD.search(whole):
            warnings.append(f"{tag}: [Client to provide] still open")
        send = f.get("send", "")
        if send and not DAY.search(send) and not re.match(r"^\s*on\s+\S", send, re.I):
            warnings.append(f"{tag}: 'Send: {send}' should read 'Day N' or 'on <event>'")
        day = DAY.search(send)
        if kind in PACED_KINDS and day:
            d = int(day.group(1))
            if prev_day is not None and d - prev_day < MIN_GAP_DAYS:
                errors.append(f"{tag}: Day {d} is under {MIN_GAP_DAYS} days after the last touch (Day {prev_day})")
            prev_day = d
    dedupe = lambda xs: list(dict.fromkeys(xs))
    return {"kind": kind, "emails": len(emails), "errors": dedupe(errors), "warnings": dedupe(warnings)}


def cmd_check(a):
    results, failed = {}, False
    for name in a.files:
        p = Path(name)
        if not p.exists():
            die(f"no such file: {p}")
        if p.name.endswith("-prospects.md"):
            if not a.json:
                print(f"SKIP  {p}  (prospect table, not an email draft)")
            continue
        r = check_text(p.read_text(encoding="utf-8"))
        results[str(p)] = r
        failed = failed or bool(r["errors"])
    if a.json:
        print(json.dumps(results, indent=2))
    else:
        for path, r in results.items():
            verdict = "FAIL" if r["errors"] else "PASS"
            print(f"{verdict}  {path}  ({r['kind'] or 'no kind'}, {r['emails']} emails)")
            for e in r["errors"]:
                print(f"  error: {e}")
            for w in r["warnings"]:
                print(f"  warn:  {w}")
    sys.exit(1 if failed else 0)


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Email drafting helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("paths")
    p.add_argument("--business")
    p.set_defaults(fn=cmd_paths)
    p = sub.add_parser("voice")
    p.add_argument("action", choices=["init"])
    p.add_argument("--business")
    p.set_defaults(fn=cmd_voice)
    p = sub.add_parser("check")
    p.add_argument("files", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
