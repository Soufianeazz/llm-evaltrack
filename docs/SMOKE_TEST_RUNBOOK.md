# Smoke Test Runbook (Post-Deploy)

## URLs

- Landing: `https://www.agentlens.one/`
- App login/signup: `https://www.agentlens.one/app`
- Demo Dashboard: `https://www.agentlens.one/dashboard?demo=1&api_key=al_demo_agentlens`
- Demo Traces: `https://www.agentlens.one/traces.html?demo=1&api_key=al_demo_agentlens`
- Demo Compliance: `https://www.agentlens.one/compliance.html?demo=1&api_key=al_demo_agentlens`

## A) Landing checks

1. Header links render and open correctly.
2. Messaging is Open-Core consistent (no conflicting Open-Source-only wording).
3. CTA buttons open demo pages with demo parameters.

## B) Auth and logout

1. Sign in at `/app`.
2. Open dashboard.
3. Click logout.
4. Expected result: direct redirect to landing page `/`.

## C) Plan entitlement checks

Use real keys from 3 different plans.

1. Starter key:
   - Prompt Debugger works
   - Agent Debugger returns `403` (blocked)
   - Compliance returns `403` (blocked)
2. Team key:
   - Agent Debugger works
   - Compliance returns `403` (blocked)
3. Scale key:
   - Compliance works

## D) Live data checks

1. In dashboard, click `Run Live Demo`.
2. Confirm:
   - Calls/KPIs increase
   - Agent traces appear
   - Prompt debugger entries appear
   - Compliance stats update

## E) API spot checks (PowerShell)

```powershell
$BASE = "https://www.agentlens.one"
$API_KEY = "al_xxx"
$headers = @{ "X-API-Key" = $API_KEY }

Invoke-RestMethod "$BASE/requests/stats" -Headers $headers
Invoke-RestMethod "$BASE/debug/requests?limit=5" -Headers $headers
Invoke-RestMethod "$BASE/traces?limit=5" -Headers $headers
Invoke-RestMethod "$BASE/compliance/stats" -Headers $headers
```

Expected:

- No 5xx responses
- Plan-restricted endpoints return clear `403` when blocked
- Allowed endpoints return data payloads
