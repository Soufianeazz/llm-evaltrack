# AgentLens

[![PyPI](https://img.shields.io/pypi/v/agentlens-monitor.svg)](https://pypi.org/project/agentlens-monitor/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/Soufianeazz/agentlens?style=social)](https://github.com/Soufianeazz/agentlens)
[![License: BSL 1.1](https://img.shields.io/badge/server-BSL%201.1-yellow.svg)](LICENSE)
[![SDK: MIT](https://img.shields.io/badge/sdk-MIT-green.svg)](agentlens/LICENSE)

> **Self-hosted LLM observability with built-in air-gap mode.** Quality scoring, agent waterfalls, prompt debugger, GDPR-native compliance workflows. Free for production self-hosting (BSL 1.1).

**🔗 [Live demo (no signup)](https://www.agentlens.one/dashboard?demo=1&api_key=al_demo_agentlens)** · **📦 `pip install agentlens-monitor`** · **🐳 [Self-host in 5 min](#install-self-hosted-in-5-minutes)**

![AgentLens Dashboard](docs/dashboard.png)

---

## Why AgentLens

Most LLM observability tools force you to choose: ship your prompts to a US-hosted SaaS, or build it yourself. AgentLens gives you a third option — a production-grade self-hosted platform that runs entirely in your infrastructure, with one Docker command.

**You get:**

- 🎯 **Quality scoring + hallucination flags** — heuristic by default, optional LLM-as-judge
- 🪵 **Agent waterfall debugging** — multi-step traces with span-level timing and cost
- 🔍 **Prompt-level inspection** — every LLM call, with full input/output and metadata
- 💰 **Cost + budget observability** — per-model, per-feature, with daily budget alerts
- 🛡️ **GDPR-native compliance** — export, retention policy, audit log, right-to-erasure
- 🔐 **Air-gap mode** — single env var disables every external integration. tcpdump-verifiable.

---

## How AgentLens compares

| | **AgentLens** | LangSmith | Langfuse | Helicone |
|---|---|---|---|---|
| Self-hosted | ✅ default | ❌ cloud-only | ✅ | ✅ |
| Air-gap mode (no outbound) | ✅ baked-in | ❌ | ⚠️ partial | ⚠️ partial |
| GDPR-native + EU-hosted cloud | ✅ | ❌ US | ⚠️ EU optional | ❌ US |
| Heuristic scoring (no judge calls) | ✅ default | ❌ paid LLM judge | ❌ paid LLM judge | ❌ |
| Agent waterfall traces | ✅ | ✅ | ✅ | ❌ |
| BSL/MIT open-core | ✅ | ❌ proprietary | MIT | MIT |
| Production cost (mid-team) | €299–2,999/mo | $39–500/seat | $$ | $$ |

**Picking guide:** Pick AgentLens if you're in regulated industry, EU-based, or air-gap matters to you. Pick LangSmith if you want a fully managed cloud and don't mind US data residency. Pick Langfuse if you want a free MIT-only path. Pick Helicone for simple proxy-style logging.

---

## Install (self-hosted in 5 minutes)

**One-line installer (recommended):**

```bash
curl -fsSL https://www.agentlens.one/install | bash
```

**OR build from source (security-conscious teams):**

```bash
git clone https://github.com/Soufianeazz/agentlens && cd agentlens
cp .env.airgap.example .env
echo "ADMIN_TOKEN=$(openssl rand -hex 32)" >> .env
docker compose up -d --build
```

→ Open `http://localhost:8000` for the dashboard.

**Add the SDK to your code:**

```bash
pip install agentlens-monitor
```

```python
import agentlens

agentlens.init(api_url="http://localhost:8000/ingest", api_key="al_...")
agentlens.patch_openai()    # auto-track every OpenAI call
agentlens.patch_anthropic() # auto-track every Anthropic call
```

---

## Trace multi-step agents

```python
from agentlens import trace_agent

with trace_agent("research_agent", input="Research market trends") as trace:
    with trace.span("retrieve_context", span_type="retrieval") as s:
        s.set_output("found 12 documents")

    with trace.span("reason_and_draft", span_type="llm", model="gpt-4o") as s:
        s.set_output("Draft ready")
        s.set_tokens(1200)
        s.set_cost(0.009)

    trace.set_output("Report complete")
```

→ Every span shows up in the agent waterfall view with timing, cost, and full I/O.

---

## Why I built this

I'm Soufian, a solo founder. I kept seeing teams stuck between two bad choices for LLM observability: ship sensitive prompts to a US SaaS, or build it themselves and abandon it after 6 weeks. The third option — a production-grade self-hostable platform with EU compliance baked in — didn't exist.

So I built it. AgentLens is what I'd want to run on my own infra: one Docker command, no telemetry, GDPR-clean, and a clear paid tier for teams that want managed operation.

If this resonates: ⭐ **a star helps the project show up in search**, and tells me to keep building.

---

## Plan packaging

| Plan | Price | What's included |
|---|---:|---|
| **Free** | €0 | Ingest API + Basic Stats (24h) + Prompt Debugger preview |
| **Starter** | €299/mo | + Prompt Debugger |
| **Team** | €999/mo | + Agent Debugger + Advanced Analytics |
| **Scale** | €2,999/mo | + Compliance / GDPR workflows + Audit log |
| **Enterprise** | €5,000+/mo | + Private Deploy + SLA + Security Package |

Self-hosting under BSL is free for any internal production use — paid plans add server-side feature tiers (Prompt/Agent Debugger, Compliance workflows, Audit Log) plus managed cloud, support, and security artifacts.

Qualified teams can request a **14-day full-feature pilot** before committing.

---

## License — dual model (Sentry / MongoDB pattern)

- **Python SDK** (`agentlens/`, on PyPI) → **MIT**. Embed in any product. No restrictions.
- **Server** (everything else in this repo) → **Business Source License 1.1**. Free for self-hosted production use. Converts to Apache 2.0 on 2030-05-11.

The BSL **only** restricts offering AgentLens itself as a competing hosted SaaS to third parties. Internal production use, modification, and redistribution within your org are explicitly permitted. See [LICENSING.md](LICENSING.md) for the plain-language guide.

---

## API quick reference

| Endpoint | Purpose |
|---|---|
| `POST /ingest` | Log an LLM call |
| `GET /requests/stats` | 24h KPIs (calls, quality, cost) |
| `GET /requests/trend` | Hourly quality trend |
| `GET /requests/worst` | Worst-quality responses |
| `GET /requests/cost-quality` | Cost vs quality per model |
| `GET /debug/requests` | Full call inspector |
| `POST /traces` + lifecycle | Agent waterfall traces |
| `GET /compliance/export` | CSV/JSON export |
| `POST /compliance/retention` | Auto-delete policy |
| `GET /compliance/audit-log` | Audit events (admin) |

Full docs in `api/main.py` and `docs/SELF_HOST.md`.

---

## Managed Cloud Option

Use [agentlens.one](https://www.agentlens.one) for managed rollout, buyer-ready trust artifacts, and plan-based feature access. Hosted in Frankfurt (EU), GDPR-native by design.

---

## Operations & Documentation

- [`docs/SELF_HOST.md`](docs/SELF_HOST.md) — full self-host guide
- [`LICENSING.md`](LICENSING.md) — license model in plain English
- Source of truth + deploy path: [`docs/SOURCE_OF_TRUTH.md`](docs/SOURCE_OF_TRUTH.md)
- Pre-call deploy checklist: [`docs/DEPLOY_CHECKLIST_PRECALL.md`](docs/DEPLOY_CHECKLIST_PRECALL.md)
- Smoke tests after deploy: [`docs/SMOKE_TEST_RUNBOOK.md`](docs/SMOKE_TEST_RUNBOOK.md)

Recommended env hardening for production:

```
CORS_ALLOWED_ORIGINS=https://www.agentlens.one,https://agentlens.one
AGENTLENS_AIRGAP=1   # for fully isolated deployments
```

---

## Contributing & Support

- 🐛 **Bug reports + feature requests:** [GitHub Issues](https://github.com/Soufianeazz/agentlens/issues)
- 💬 **Questions / pilot requests:** soufian.azzaoui48@gmail.com
- ⭐ **Star the repo** if you'd like to see this category mature

If you're shipping AgentLens in production, I'd love to hear about it — and a quote / case study (with logo) gets you a discount on the Scale tier.
