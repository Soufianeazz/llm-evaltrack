# llm-evaltrack — Project Context for Claude

## What this is
LLM Observability & Monitoring Tool. Self-hosted, framework-agnostic alternative to LangSmith/Helicone. Built with FastAPI + SQLite. Live on Railway.

## Live URLs
- Dashboard: https://llm-evaltrack-production.up.railway.app
- Agent Debugger: https://llm-evaltrack-production.up.railway.app/traces.html
- Prompt Debugger: https://llm-evaltrack-production.up.railway.app/debug.html
- Compliance: https://llm-evaltrack-production.up.railway.app/compliance.html
- GitHub: https://github.com/Soufianeazz/llm-evaltrack
- PyPI: `pip install llm-evaltrack` (v0.1.0)

## Stack
- Python 3.13, FastAPI, SQLite (aiosqlite), SQLAlchemy async
- Dashboard: plain HTML + Chart.js — no frontend build step
- Deploy: Railway.app (auto-deploys on git push to main)
- SDK: `llm_observe` package (published on PyPI)

## Project Structure
```
api/
  main.py                  # FastAPI app, router registration, lifespan
  schemas.py               # Pydantic models
  routes/
    ingest.py              # POST /ingest
    dashboard.py           # GET /requests/* (stats, trend, worst, etc.)
    alerts.py              # GET/POST/DELETE /alerts/budget
    debug.py               # GET /debug/requests, /debug/requests/{id}
    compliance.py          # GET/POST /compliance/* (export, retention, audit)
    traces.py              # GET/POST /traces, /traces/{id}, /traces/{id}/spans
dashboard/
  index.html               # Main dashboard
  debug.html               # Prompt debugger
  traces.html              # Agent debugger (waterfall timeline)
  compliance.html          # GDPR compliance page
evaluation/
  engine.py                # LLM Judge (Claude) + heuristic fallback
  quality.py               # Quality heuristics
  hallucination.py         # Hallucination detection
llm_observe/               # SDK package (published to PyPI)
  __init__.py              # init, track_llm_call, patch_openai, patch_anthropic, trace_agent, span
  tracker.py               # HTTP fire-and-forget shipping
  tracing.py               # trace_agent() + span() context managers
  integrations/
    openai.py              # monkey-patch OpenAI client
    anthropic.py           # monkey-patch Anthropic client
pipeline/
  worker.py                # async queue worker, evaluation + budget alert check
storage/
  models.py                # SQLAlchemy models: Request, Evaluation, BudgetAlert, Trace, Span, AuditLog, RetentionPolicy
  database.py              # SQLite engine, session factory
```

## Database Models
- `requests` — LLM calls (input, output, prompt, model, metadata with cost_usd)
- `evaluations` — quality_score, hallucination_score, flags, explanation
- `budget_alerts` — daily_budget_usd, webhook_url, triggered_today
- `traces` — agent runs (name, status, input, output, total_cost, duration)
- `spans` — individual steps in a trace (type: llm/tool/retrieval/decision/custom)
- `audit_log` — compliance events
- `retention_policy` — auto-delete config

## API Endpoints
- `POST /ingest` — ingest an LLM call
- `GET /requests/stats` — 24h KPIs
- `GET /requests/trend` — hourly quality trend
- `GET /requests/worst` — worst responses
- `GET /requests/regression` — quality regression detection
- `GET /requests/root-cause` — worst prompts by failure rate
- `GET /requests/cost-quality` — per-model cost vs quality
- `GET/POST/DELETE /alerts/budget` — budget alert config
- `GET /debug/requests` — search/filter LLM calls
- `GET /debug/requests/{id}` — full detail view
- `GET /compliance/export` — CSV/JSON export
- `POST /compliance/retention` — set retention policy
- `DELETE /compliance/requests` — bulk delete
- `GET /compliance/audit-log` — audit events
- `POST /traces` — create agent trace
- `POST /traces/{id}/end` — end trace
- `POST /traces/{id}/spans` — add span
- `POST /traces/{id}/spans/{sid}/end` — end span
- `GET /traces` — list traces
- `GET /traces/{id}` — trace detail with all spans

## SDK Usage
```python
import llm_observe

# Basic setup
llm_observe.init(api_url="https://llm-evaltrack-production.up.railway.app/ingest")
llm_observe.patch_openai()     # auto-track all OpenAI calls
llm_observe.patch_anthropic()  # auto-track all Anthropic calls

# Agent tracing
from llm_observe import trace_agent, span

with trace_agent("my_agent", input="user question") as trace:
    with trace.span("search", span_type="retrieval") as s:
        s.set_output("results...")
    with trace.span("generate", span_type="llm", model="gpt-4o") as s:
        s.set_output("answer")
        s.set_tokens(500)
        s.set_cost(0.003)
    trace.set_output("final answer")
```

## Start Locally
```powershell
cd "C:\Users\Soufiane\Saved Games\llm-observability"
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # optional, enables LLM judge
python -m uvicorn api.main:app --reload
# Dashboard: http://localhost:8000
```

## Deploy
Push to main branch → Railway auto-deploys. No manual steps needed.

## Key Decisions
- SQLite (not Postgres) — simple, no extra service needed for MVP
- In-process asyncio.Queue (not Redis) — swap-ready but simple for now
- Evaluation is async (fire-and-forget after ingest)
- No auth on API — open CORS, intentional for MVP
- Cost calculated in SDK at call time, stored in metadata JSON field

## Next Steps
1. Outreach & Marketing (first paying customer)
2. README update (document Agent Debugging + new features)
3. PyPI v0.2.0 release (trace_agent SDK)
