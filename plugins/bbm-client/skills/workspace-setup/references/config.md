# Workspace configuration

The bootstrap writes `bbm-client.json` in the workspace root. All path values are relative to that file. No machine-specific global pointer is written. `BBM_CLIENT_CONFIG` can explicitly select that file; otherwise helpers search upward from the working directory. A missing or invalid explicit config fails without falling back elsewhere.

| Key | Meaning |
|---|---|
| OWNER_NAME | Owner display name |
| WORKSPACE_ROOT | `.`: the config directory |
| VAULT_PATH | The tracked knowledge vault |
| WORKSPACE_MAP | Folder and record conventions |
| RAW_SOURCES_PATH | Supplied source Markdown |
| WIKI_PATH | Wiki pages, index and log |
| STATE_PATH | The selected business's changing work |
| PROPOSED_PATH | Protected drafts and unresolved claims |
| BOUNDARIES_FILE | Approval and privacy rules |

All configured knowledge paths must exist within the vault. Setup supports one initial business. Add another business only on explicit owner direction, preserving access boundaries; source ingestion must not invent one. Workspace-specific knowledge stays out of the plugin.
