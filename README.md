# AgentLens

[![PyPI](https://img.shields.io/pypi/v/agentlens-monitor.svg)](https://pypi.org/project/agentlens-monitor/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/Soufianeazz/agentlens?style=social)](https://github.com/Soufianeazz/agentlens)

> Open-core observability for LLM applications: quality scoring, prompt debugging, agent tracing, cost control, and compliance workflows.

**Live demo:** [www.agentlens.one](https://www.agentlens.one/dashboard?demo=1&api_key=al_demo_agentlens)

![AgentLens Dashboard](docs/dashboard.png)

---

## Plan Packaging (Current)

| Plan | Price | Included Features |
|---|---:|---|
| Free | EUR 0 | Ingest API + Basic Stats (24h) |
| Starter | EUR 299 / month | + Prompt Debugger |
| Team | EUR 999 / month | + Agent Debugger + Advanced Analytics |
| Scale | EUR 2,999 / month | + Compliance / GDPR workflows |
| Enterprise | EUR 5,000+ / month | + Private Deploy, SLA, Security Package |

Starter, Team, and Scale run on 12-month terms billed monthly.

---

## Why AgentLens

Most LLM teams can ship features. Fewer can run them safely at scale.

AgentLens gives you:

- Automatic quality scoring and hallucination flags
- Prompt-level debugging with detailed call inspection
- Agent waterfall debugging with span-level visibility
- Cost and budget observability
- Compliance export, retention, and audit logs

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

## Legacy Code Snapshot

Earlier public snapshots remain available in repository history and tags. The active product direction is now **open core**.

For historical snapshots, browse tags/commits in this repository.
