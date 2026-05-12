# AgentLens — Self-Hosted Air-Gapped Deployment

Built for pilots like {primary_workflow} / {secondary_workflow} where **zero external data egress** is mandatory.

## What "air-gapped" means here

When `AGENTLENS_AIRGAP=1` is set:

- **No Anthropic calls** — heuristic evaluation only (no LLM judge).
- **No Stripe / SendGrid / Resend** — billing & email integrations skipped.
- **No outbound webhooks** outside loopback / RFC1918 ranges.
- **No telemetry** of any kind.

You can verify with `tcpdump` after startup — only port 8000 traffic from your own clients.

## Minimum infrastructure footprint

| Resource | Minimum | Recommended |
|----------|--------:|------------:|
| CPU      | 1 vCPU  | 2 vCPU      |
| RAM      | 512 MB  | 1 GB        |
| Disk     | 5 GB    | 20 GB       |
| OS       | Linux x86_64 with Docker 24+ | Ubuntu 22.04 LTS |

SQLite + the in-process queue keeps the footprint tiny. Postgres is **not** required.

## Quick start

```bash
git clone https://github.com/Soufianeazz/agentlens.git
cd agentlens
cp .env.airgap.example .env

# Generate a strong admin token
python3 -c "import secrets; print('ADMIN_TOKEN=' + secrets.token_urlsafe(48))" >> .env

docker compose up -d
docker compose logs -f agentlens   # watch startup
```

Open `http://<host>:8000` — you should see the dashboard.

## Bootstrap your first API key

The first key is created from the host with the admin token:

```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "X-Admin-Token: $(grep ^ADMIN_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"label": "primary_workflow-pilot", "role": "admin"}'
```

Save the returned `key` — that's what your workloads will use.

## Instrument workloads

### Ollama (provider-agnostic, works for any local LLM)

Ollama exposes an OpenAI-compatible API on `:11434`, so the standard SDK patch covers it:

```python
import os
import openai
import agentlens

agentlens.init(
    api_url="http://<agentlens-host>:8000/ingest",
    api_key=os.environ["AGENTLENS_API_KEY"],
)
agentlens.patch_openai()  # patches OpenAI SDK including Ollama-compatible clients

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # any non-empty string
)

resp = client.chat.completions.create(
    model="llama3.1",
    messages=[{"role": "user", "content": "Hello"}],
)
# Auto-tracked — appears in /debug.html within seconds.
```

### Microsoft GraphRAG retrieval workflow

Wrap your multi-hop pipeline with `trace_agent` and one `span` per step. Citation faithfulness shows up as a flag on the synthesis span.

```python
from agentlens import trace_agent

with trace_agent("primary_workflow_query", input=user_question) as t:
    with t.span("expand_subgraph", span_type="retrieval") as s:
        nodes = graphrag.expand(user_question, hops=2)
        s.set_output(f"{len(nodes)} nodes, {len(edges)} edges")

    with t.span("rank_passages", span_type="retrieval") as s:
        passages = ranker.score(nodes)
        s.set_output(f"top-{len(passages)}: {[p.id for p in passages[:5]]}")

    with t.span("synthesize", span_type="llm", model="llama3.1") as s:
        s.set_input("\n".join(p.text for p in passages))
        answer, citations = llm.generate(passages, user_question)
        s.set_output(answer)
        s.set_tokens(usage.total_tokens)
        # Citation faithfulness is checked by the heuristic engine on output text.

    t.set_output(answer)
```

### Policy reasoning ({secondary_workflow})

```python
with trace_agent("secondary_workflow_sod_check", input=request_payload) as t:
    with t.span("load_policy", span_type="retrieval") as s:
        policy = load_yaml("policies/sod.yaml")
        s.set_output(policy["name"])

    with t.span("reason", span_type="llm", model="llama3.1") as s:
        decision = reasoner.evaluate(policy, request_payload)
        s.set_output(decision.json())
        s.set_tokens(usage.total_tokens)

    with t.span("verdict", span_type="decision") as s:
        s.set_output("ALLOW" if decision.allowed else "DENY")

    t.set_output("ALLOW" if decision.allowed else "DENY")
```

## Where to look in the UI

| URL | What |
|-----|------|
| `/dashboard` | 24h KPIs, quality trend, cost-vs-quality |
| `/debug.html` | Per-call inspection, filter by flag/model/quality |
| `/traces.html` | Multi-step agent waterfall — click a span to see I/O |
| `/compliance.html` | Export, retention policy, audit log |

## Backup & restore

```bash
# Backup (cron weekly)
docker run --rm \
  -v agentlens-data:/data \
  -v $PWD:/backup \
  alpine tar czf /backup/agentlens-$(date +%F).tgz /data

# Restore
docker compose down
docker run --rm \
  -v agentlens-data:/data \
  -v $PWD:/backup \
  alpine tar xzf /backup/agentlens-2026-05-15.tgz -C /
docker compose up -d
```

## Upgrades

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

The schema migrates itself on startup (additive only — your data stays).

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Dashboard shows 0 calls | `docker compose logs agentlens` for ingest errors; verify `api_url` in SDK |
| `403 Invalid API key` | Key was disabled — recreate via `/admin/api-keys` |
| Quality scores all `[heuristic]` | Expected in air-gap mode. Heuristics are fully local. |
| Container restarts on OOM | Bump `mem_limit` in `docker-compose.yml` to 1g |

## Health check

```bash
curl http://localhost:8000/healthz     # → {"status":"ok"}
```
