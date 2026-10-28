# First-time setup

1. Clone your private repository using GitHub Desktop or `git clone <your-private-repository-url> "Command Center"`. Sign in with your own GitHub account. If already cloned, use that folder; do not create a second copy.
2. Open the folder in Claude Code or Codex. Read AGENTS.md. Neither app is installed by this repository. Python 3.10+ is needed for helper scripts (`python3 --version`, or `py --version` on Windows).
3. Install **bbm-client** using docs/SKILLS.md. Choose only the host(s) you use. Restart the assistant afterward.
4. Ask: "Use workspace-start and confirm my configured vault paths." The config uses relative paths, so it follows the checkout across computers. Do not import another workspace's global configuration.
5. Add your first text meeting export or note: "Use source-capture to save this for {{BUSINESS}}, then wiki-ingest to file it." Manually exported notes work immediately; dictation and automatic meeting capture are separate capabilities.
6. Ask: "What did we decide?" and then "Audit the wiki." Verify the answer links to your source. A synthetic example is in docs/EXAMPLE.md; do not treat it as a real commitment.

Daily: ask for the next useful step, save the session, and request Git sync when ready. Review changes before uploading. Pull workspace updates only with a clean tree and fast-forward (`git pull --ff-only`); stop on conflicts. Plugin updates never pull or upload your notes.

Check the business CONTEXT.md and your preferences file with your assistant. Fill unknowns only from your own confirmed facts. No provider credentials belong here.
