# Pre-Call Deploy Checklist

## 1) Branch and workspace

1. Confirm path: `agentlens-live-publish`.
2. Run `git status`.
3. Ensure no unrelated/unreviewed file changes.

## 2) Hardening checks

1. Confirm CORS allowlist is configured:
   - `CORS_ALLOWED_ORIGINS=https://www.agentlens.one,https://agentlens.one`
2. Confirm plan gating is active in backend:
   - `prompt_debugger` requires Starter+
   - `agent_debugger` requires Team+
   - `compliance_gdpr` requires Scale+
3. Confirm demo links include `demo=1&api_key=al_demo_agentlens`.

## 3) Build/syntax checks

1. Python syntax check:
   - `python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('api').rglob('*.py')]; print('ok')"`
2. Optional local run:
   - `uvicorn api.main:app --reload`

## 4) Deploy

1. Commit and push `main`.
2. Trigger Railway deploy (or verify auto-deploy).
3. Wait until deployment is green.

## 5) Post-deploy smoke

1. Open landing page.
2. Open demo dashboard/traces/compliance from CTA.
3. Login and verify plan-restricted screens:
   - Starter key: Prompt Debugger allowed, Agent Debugger blocked
   - Team key: Agent Debugger allowed, Compliance blocked
   - Scale key: Compliance allowed
4. Test logout redirects to `/`.

## 6) Call safety fallback

If any issue appears before call:

1. Use demo links on landing for stable walkthrough.
2. Use `Run Live Demo` in dashboard for fresh data generation.
3. Keep one approved account in each plan for entitlement demo.
