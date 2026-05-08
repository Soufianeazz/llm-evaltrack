# AgentLens Source Of Truth

This repository path is the single deployment source:

- `C:\Users\Soufiane\Documents\New project\agentlens-live-publish`

Operational rule:

1. All production edits happen here only.
2. Deploy only the commit currently on this repository `main` branch.
3. Ignore sibling folders (`agentlens-live`, `agentlens-live-deploy`) for production changes.
4. Before each deploy, run:
   - `git status` (must be clean except intentional changes)
   - `git log -1 --oneline` (capture deploy commit id)

Environment baseline expected in Railway:

- `ADMIN_TOKEN`
- `RESEND_API_KEY` (if signup/billing emails are used)
- `CORS_ALLOWED_ORIGINS` (comma-separated allowlist)
