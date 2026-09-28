Install the BBM Buzz Agents plugin on this machine for both Claude Code and Codex, then set up my agent config. Do only what's below. Don't create any agents yet.

1. **Find what's installed.** Check which of `claude` and `codex` exist on this machine, their versions, the OS, and which Python the Buzz agents use (3.10+ needed). Report before changing anything if something is missing.

2. **Claude Code.** Run, in this order:
   ```
   claude plugin marketplace add "Brand-Building-Machine/bbm-buzz-agents#release"
   claude plugin install bbm-agents@bbm-buzz-agents
   ```
   The `add` command rewrites the marketplace entry in `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`) and drops auto-update. **After** it runs, open that file and set `"autoUpdate": true` inside `extraKnownMarketplaces.bbm-buzz-agents` — change nothing else. Confirm the file is still valid JSON, then run `claude plugin list` and confirm `bbm-agents` is installed and enabled.

3. **Codex** (skip if Codex isn't installed):
   ```
   codex plugin marketplace add Brand-Building-Machine/bbm-buzz-agents --ref release
   codex plugin add bbm-agents@bbm-buzz-agents
   codex plugin list
   ```
   Confirm `bbm-agents` is installed.

4. **YouTube skill dependencies.** Check `yt-dlp` is importable by the Python the agents use (`python3 -m yt_dlp --version`; Windows `py -m yt_dlp --version`). If it's missing, tell me the command to install it and wait for my yes. Don't install anything globally without asking. Don't set up any API keys.

5. **Workspace config.** Run the `workspace-config` skill from the plugin: find my workspace repo, propose every value in one message, and wait for my confirmation before writing.

6. **Report** in a few lines: what got installed where, versions, the config file path, anything missing or skipped. Then tell me to restart Buzz, and that after the restart I can say "install Agent Builder" to start adding agents.
