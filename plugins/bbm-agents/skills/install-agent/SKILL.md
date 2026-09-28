---
name: install-agent
description: Install one of the prebuilt bbm-agents Buzz agents (chief of staff, Agent Builder, Research Lead, YouTube Desk, SEO Desk, Meta Ads Desk, Email Desk) as an owner-reviewed draft, or update an installed one to the latest version. Use when the owner says "install/add/set up the <agent>", "update my agents", "which agents are available", or "are my agents up to date". Never writes or rewrites a persona — it only fills in the owner's names and paths.
---

# install-agent

The personas in this plugin are finished. **Do not write, edit, shorten or "improve" them.** This skill fills in the owner's names and paths, shows the result, and opens a draft the owner approves in Buzz Desktop. That is all it does.

The script is `scripts/agents.py`, relative to this skill's folder (the folder containing this SKILL.md). Run it with `python3` on macOS/Linux, `python` or `py` on Windows.

## Steps

1. **Config first.** `python3 <skill dir>/scripts/agents.py config`. If it says no config found, run the `workspace-config` skill, then come back.

2. **See what's available and what's installed.**
   `agents.py list` and `agents.py status`.

3. **Check the live roster before drafting.** An agent that already does this job may exist under another name (e.g. the owner's chief of staff is "Truth" or "Simple Jack"). If one exists, ask the owner in one line: update that agent to this version, or leave it? Never replace an existing agent without a yes.

4. **Show the owner what they'll get.** `agents.py render <role>`. Post the name and description, and say the full persona is in the draft for them to read. If the script exits 2 with unresolved placeholders, fix the config with `workspace-config` — never fill a gap by guessing or by editing the persona.

5. **Check what the role needs.** Each persona's frontmatter lists `runtimes`, `requires_skills` and `requires_subagents`.
   - Research Lead and Agent Builder need the **Claude** runtime (subagents). Tell the owner to pick Claude when they save the draft.
   - YouTube skills need Python 3.10+ and `yt-dlp` available *inside Buzz*. Check with the same Python the skill will use. If missing, say what's missing and the install command; install only with the owner's yes, never globally without asking.
   - SEO Desk needs Python 3.10+ only. It reads the brand folder, so run `brand-bible` first if the owner hasn't. A Google PageSpeed Insights API key is optional (speed checks); it must be the owner's own, set as `PAGESPEED_API_KEY`.
   - Meta Ads Desk needs Python 3.10+ only and reads the brand folder (`brand-bible` first). Live account access is Meta's own ads connector: offer the one-line setup in `meta-audit/references/connector.md` once the agent is saved; the owner signs in with their Meta login. Without it the desk works from Ads Manager exports.
   - Email Desk needs Python 3.10+ only and reads the brand folder (`brand-bible` first). Its first job is the owner's email voice file, built from 10 to 20 emails they actually sent (`email-sequences`). It never sends email.
   - A Gemini key is optional (no-caption videos, corpus extraction). It must be the owner's own. Never copy one from anywhere.

6. **Open the draft** in the current channel:
   - New agent: `agents.py draft <role> --channel <current-channel-uuid>`
   - Update existing: `agents.py draft <role> --channel <uuid> --update "<current agent name>"`
   Use `--dry-run` first if anything looks off.

7. **Report exactly one of these, honestly:**
   - "Draft ready for your review in Buzz Desktop — it isn't an agent until you save it."
   - The draft failed or didn't appear → **do not resend.** Run `agents.py render <role>` and give the owner the name, description and full persona to paste into Agents → New agent.
   Drafts only open on the owner's own machine. If someone other than the owner asked, say the owner has to ask directly.

8. **After the owner saves it**, tell Agent Builder (or update the `agent-roster` memory slug yourself if you are Agent Builder) that it's live. Then offer one realistic test task for the new agent.

## Order for a fresh workspace

Agent Builder → chief of staff (usually an update of an existing one) → YouTube Desk → Research Lead → SEO Desk → Meta Ads Desk → Email Desk.

## Updates

When `status` shows "UPDATE AVAILABLE", offer the owner a `draft-update` for that agent, one at a time. The installed persona's version stamp (`<!-- bbm-agents: role vN -->`, last line) is how the script knows — leave it in.
