---
name: workspace-setup
description: "Create a portable client vault starter or orient an existing workspace for first-time use. Includes instructions, maps, README and initial knowledge records."
---

# Workspace setup

Inspect the selected folder and existing instructions first. This installs workspace files only, without accounts, other plugins, schedules or external writes. Use the name, business and folder already provided; ask only for missing values.

Run the script in this skill's `scripts/` directory:

```
python3 bootstrap.py --destination "/chosen/Command Center" --owner "Sam" --person sam --business example-business
```

On Windows use `py` or `python`. The default is a preview. Add `--apply` when setup is authorized. The script refuses differing existing files before writing anything; identical files are retained. To adapt an existing README or rules, generate into a fresh local scratch folder, review the differences, then merge deliberately. Never delete existing instructions to get past a conflict. Preserve existing notes, Git history and skills.

Open the resulting folder in the assistant and follow docs/START_HERE.md. Run wiki.py paths and lint, then try a synthetic source in a temporary workspace. Explain what is configured versus actually installed or connected. The owner chooses when to connect services. No Git commit/push is performed by setup.


Configuration keys and lookup: [config reference](references/config.md).
