# Connecting Google Ads (Composio)

Google Ads Desk reads the owner's account through Composio, a free service that holds the Google sign-in so no API keys or developer tokens live on the machine. Access is read-only in these skills: the script only ever asks Google Ads for reports.

Walk the owner through it one step at a time. Tell them exactly what to type, and wait after each step.

## Mac (and Linux)

1. **Install the CLI.** In Terminal:
   `curl -fsSL https://composio.dev/install | sh`
   Then open a new Terminal window and check: `composio --version`.
2. **Sign in to Composio:** `composio login`. A browser opens; they sign in or create a free account.
3. **Connect Google Ads:** `composio link googleads`. A browser opens; they sign in with the **Google login that has access to their Google Ads account** and allow access.
4. **Check it:** run `gads.py accounts` (from the `google-ads-audit` skill). Their account should be listed by name.

## Windows

Composio's CLI runs inside WSL (Windows Subsystem for Linux), not in Windows itself. `gads.py` finds it there automatically.

1. **Install WSL** if it isn't already: open PowerShell **as administrator**, run `wsl --install`, restart the computer when asked, then open "Ubuntu" from the Start menu once and create a user name and password.
2. **In the Ubuntu window**, install the CLI: `curl -fsSL https://composio.dev/install | sh`, close and reopen Ubuntu, check `composio --version`.
3. Still in Ubuntu: `composio login`, then `composio link googleads` (same as Mac steps 2-3). If a browser doesn't open by itself, copy the link it prints into a browser.
4. **Check it** from the agent: `gads.py paths` should say `composio: inside WSL`, and `gads.py accounts` should list the account.

## When it doesn't work

| What you see | What it means | Fix |
|---|---|---|
| `composio isn't installed or isn't on PATH` | CLI missing, or a new terminal wasn't opened after installing | Repeat step 1; on Mac open a new Terminal; set `COMPOSIO_BIN` to the full path if needed |
| `Is Google Ads linked?` or a Composio connection error | `composio link googleads` wasn't finished | Run it again and complete the browser step |
| `NOT_ADS_USER` | The Google login linked has no Google Ads access | Link again with the right Google login, or have the account owner add that login in Google Ads (Admin → Access and security) |
| `CUSTOMER_NOT_ENABLED` | That account is cancelled, suspended or never finished setup | Pick another account, or finish billing setup in Google Ads |
| `USER_PERMISSION_DENIED` | The account is reachable only through a manager (MCC) account | `gads.py use <id> --login <manager id>` |
| One account shows as `(hidden)` | Composio masks the manager ID saved on the connection | `gads.py accounts --manager <manager id>` |
| Several Composio Google Ads connections | The CLI picks one | Set `GOOGLE_ADS_COMPOSIO_ACCOUNT` to the one to use (`composio connections list` shows them) |

No Composio at all: the audit can still run from exports (`paste-exports.md`), and planning can proceed without live keyword volumes, clearly labelled as such.
