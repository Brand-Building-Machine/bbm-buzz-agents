# Meta's ads connector: setup and use

Meta's official ads connector is an MCP server at `https://mcp.facebook.com/ads`. The owner signs in with their own Meta (Facebook) login and picks the business portfolio to share. No developer app, no token, no third party in between. It is in open beta (since April 2026).

Every Meta skill works without it: audits run on an Ads Manager export, and any approved plan can be built by hand in Ads Manager. The connector makes reads live and lets approved changes be applied for the owner.

## Connect it (owner's machine, once)

**Claude Code:**
```
claude mcp add --transport http meta-ads https://mcp.facebook.com/ads
```
Then in a Claude Code session run `/mcp`, pick `meta-ads`, and sign in with Facebook in the browser window.

**Codex:**
```
codex mcp add meta-ads --url https://mcp.facebook.com/ads
codex mcp login meta-ads
```

**Claude desktop or claude.ai:** Settings → Connectors → Add custom connector → paste the URL → Connect.

On the Meta screen, choose the business portfolio that owns the ad account. Restart Buzz afterwards so agents start fresh sessions.

## Keep writes on "ask me"

The connector applies changes the moment they are called. **It has no draft mode.** Tell the owner to leave its write tools (create, update, activate) on "ask every time" / "needs approval" in their app's permission settings. The meta-launch skill adds its own approval step on top. Read tools can be set to always allow.

## Using it

- Discover tools from the connector itself. Names seen so far include `ads_get_ad_accounts`, `ads_get_pages_for_business`, `ads_insights_*`, `ads_get_dataset_details`, `ads_get_dataset_quality`, `ads_get_errors`, `ads_create_campaign`, `ads_create_ad_set`, `ads_create_ad`, `ads_update_entity`, `ads_activate_entity`. A name in this file is not proof the owner's connection has it; check the list.
- Before any read, confirm the account with the owner by **name and id**, even if there is only one.
- Save large read results to a file in the reports folder and work from the file.

## When it doesn't work

| Symptom | What to do |
|---|---|
| "is_ads_mcp_enabled: false" or "account not enabled" | Meta is rolling access out in phases. Nothing to fix on our side. Use an export for now and try again later |
| Sign-in loops or shows no ad accounts | The person signing in needs a role on the ad account (Admin or Advertiser) inside that business portfolio. Check in Meta Business Settings → Accounts → Ad accounts → People |
| A tool errors mid-query | Retry a **read** once. Never retry a **write** blindly: read the object back first, then decide |
| Connector not listed in the session | It was added after the session started. Restart the agent (Buzz: restart Buzz) |
