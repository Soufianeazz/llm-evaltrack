# AgentLens

[![PyPI](https://img.shields.io/pypi/v/agentlens-monitor.svg)](https://pypi.org/project/agentlens-monitor/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/Soufianeazz/agentlens?style=social)](https://github.com/Soufianeazz/agentlens)
[![License: BSL 1.1](https://img.shields.io/badge/server-BSL%201.1-yellow.svg)](LICENSE)
[![SDK: MIT](https://img.shields.io/badge/sdk-MIT-green.svg)](agentlens/LICENSE)

> Open-core observability for LLM applications: quality scoring, prompt debugging, agent tracing, cost control, and compliance workflows.

**Live demo:** [www.agentlens.one](https://www.agentlens.one/dashboard?demo=1&api_key=al_demo_agentlens)

![AgentLens Dashboard](docs/dashboard.png)

---

## Plan Packaging (Current)

| Plan | Price | Included Features |
|---|---:|---|
| Free | EUR 0 | Ingest API + Basic Stats (24h) + Prompt Debugger Preview (demo/read-only) |
| Starter | EUR 299 / month | + Prompt Debugger |
| Team | EUR 999 / month | + Agent Debugger + Advanced Analytics (+ Compliance readiness preview) |
| Scale | EUR 2,999 / month | + Compliance / GDPR workflows |
| Enterprise | EUR 5,000+ / month | + Private Deploy, SLA, Security Package |

Starter, Team, and Scale run on 12-month terms billed monthly.
Paid plans (Starter/Team/Scale/Enterprise) are managed-plan features with server-side entitlement checks.
Qualified teams can request an official **14-day full-feature pilot** before committing to a paid tier.

Commercial-first positioning:

- Open-core for evaluation
- Paid plans for production operations
- Entitlements enforced server-side per plan

---

## Why AgentLens

Most LLM teams can ship features. Fewer can run them safely at scale.

AgentLens gives you:

- Automatic quality scoring and hallucination flags
- Prompt-level debugging with detailed call inspection
- Agent waterfall debugging with span-level visibility
- Cost and budget observability
- Compliance export, retention, and audit logs

## FAQ: Why pay if core code is public?

The public core is intentionally limited to evaluation and integration speed.
Paid plans cover production reliability and accountability:

- Managed operation and updates
- SLA-backed support response
- Security package for enterprise procurement
- Server-side gated advanced capabilities (Prompt Debugger, Agent Debugger, advanced analytics, compliance workflows)

## License

AgentLens uses a **dual-license** model (Sentry / MongoDB pattern):

- **Python SDK** (`agentlens/`, `pip install agentlens-monitor`) — **MIT**.
  Embed it in any product, commercial or not. No restrictions.
- **Server** (everything else in this repository) — **Business Source License 1.1**.
  Free for self-hosting your own LLM observability. Converts to Apache 2.0 on
  2030-05-11 (standard BSL clause).

The BSL only restricts **offering AgentLens itself as a competing hosted service**
to third parties. Internal production use, modification, and redistribution
within your organization are explicitly permitted.

See [LICENSING.md](LICENSING.md) for the plain-language guide and
[LICENSE](LICENSE) for the binding terms.

---

## Quickstart

```bash
pip install agentlens-monitor
```

```python
import agentlens

agentlens.init(api_url="http://localhost:8000/ingest")
agentlens.patch_openai()
agentlens.patch_anthropic()
```

Run the API:

```bash
git clone https://github.com/Soufianeazz/agentlens
cd agentlens
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Open:

- `http://localhost:8000/dashboard`
- `http://localhost:8000/debug.html`
- `http://localhost:8000/traces.html`
- `http://localhost:8000/compliance.html`

---

## SDK and Tracing

Track single calls:

```python
agentlens.track_llm_call(
    input="What is the capital of France?",
    output="Paris.",
    prompt="You are a helpful assistant.",
    model="gpt-4o",
    metadata={"feature": "qa", "cost_usd": 0.0003},
)
```

Trace multi-step agents:

```python
from agentlens import trace_agent

with trace_agent("research_agent", input="Research market trends") as trace:
    with trace.span("retrieve_context", span_type="retrieval") as s:
        s.set_output("Context ready")

    with trace.span("reason_and_draft", span_type="llm", model="gpt-4o") as s:
        s.set_output("Draft ready")
        s.set_tokens(1200)
        s.set_cost(0.009)

    trace.set_output("Report complete")
```

---

## API Overview

- `POST /ingest`
- `GET /requests/stats`
- `GET /requests/trend`
- `GET /requests/worst`
- `GET /requests/cost-quality`
- `GET /requests/root-cause`
- `GET /debug/requests`
- `POST /traces`
- `GET /traces`
- `GET /compliance/export`
- `POST /compliance/retention`
- `GET /compliance/audit-log`

---

## Managed Cloud Option

Use [agentlens.one](https://www.agentlens.one) for managed rollout, buyer-ready trust artifacts, and plan-based feature access.

---

## Operations Notes

- Source of truth and deploy path: [docs/SOURCE_OF_TRUTH.md](docs/SOURCE_OF_TRUTH.md)
- Pre-call deploy checklist: [docs/DEPLOY_CHECKLIST_PRECALL.md](docs/DEPLOY_CHECKLIST_PRECALL.md)
- Smoke tests after deploy: [docs/SMOKE_TEST_RUNBOOK.md](docs/SMOKE_TEST_RUNBOOK.md)

Recommended env hardening:

- `CORS_ALLOWED_ORIGINS=https://www.agentlens.one,https://agentlens.one`

---

## Legacy Code Snapshot

Earlier public snapshots remain available in repository history and tags. The active product direction is now **open core**.

For historical snapshots, browse tags/commits in this repository.
