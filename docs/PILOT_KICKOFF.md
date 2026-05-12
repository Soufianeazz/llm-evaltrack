# {primary_workflow} / {secondary_workflow} — 14-Day Pilot Kickoff

**Pilot owner:** the pilot customer (technical + business lead)
**Workloads:** {primary_workflow} (GraphRAG retrieval+answer), {secondary_workflow} (policy reasoning over YAML)
**Stack:** Ollama, Microsoft GraphRAG, Python ingestion + Next.js UI, fully self-hosted Linux
**Review slots:** Tue 16:00–16:30 CET, Fri 11:00–11:30 CET
**Day 0:** _set on call_ — Day 14: _Day 0 + 14_

---

## Answers to the pilot customer's pre-kickoff questions

### 1. Air-gapped self-host — no calls to Anthropic judge / Stripe / Resend?

**Confirmed.** Set `AGENTLENS_AIRGAP=1` (default in `.env.airgap.example` and baked into the Dockerfile).

That single flag enforces:
- LLM judge → forced off, heuristic evaluation only (`evaluation/engine.py`).
- Budget-alert webhooks → blocked unless target is loopback / RFC1918 (`pipeline/worker.py`).
- Stripe / SendGrid / Resend / Anthropic SDKs → never imported at runtime when their env vars are unset.

Verify with `tcpdump -i any 'not port 8000 and not arp'` on the host. Should be silent under load.

### 2. Minimum infra footprint

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 512 MB | 1 GB |
| Disk | 5 GB | 20 GB (covers 14d of trace data with margin) |
| DB | SQLite (built-in) — no Postgres needed for the pilot |

### 3. Ollama instrumentation — auto or manual?

Both work. **Recommendation: manual `trace_agent()` for the GraphRAG flow** — gives you the per-step waterfall that matches your "5-min root-cause" success criterion.

For raw Ollama LLM calls outside an agent run, `agentlens.patch_openai()` auto-tracks them via the OpenAI-compatible Ollama endpoint at `http://localhost:11434/v1`. See `docs/SELF_HOST.md` for snippets.

---

## Kickoff agenda (Tue 16:00 CET, 30 min)

| Time | Topic | Owner |
|------|-------|-------|
| 0–5  | `docker compose up` walkthrough on his Linux host | the pilot customer shares screen |
| 5–10 | Bootstrap admin token + first API key | Soufian |
| 10–20| Live-instrument one {primary_workflow} query end-to-end (`trace_agent` + 3 spans) | Pair |
| 20–25| Show dashboard, debug, traces UI — what he'll see Tue/Fri | Soufian |
| 25–30| Pin success metrics + Day 7 / Day 14 checkpoints | Both |

## Success criteria — measurable

| # | Criterion | How we measure |
|---|-----------|----------------|
| 1 | Root-cause < 5 min on multi-step traces | the pilot customer starts a stopwatch when he sees a failed trace, stops when he can name the failing span. Target met if median ≤ 5 min over 5 incidents. |
| 2 | Visibility into hallucination / citation-faithfulness rates per workflow | Daily `/requests/stats` per workflow tag (`metadata.feature=primary_workflow` vs `secondary_workflow`). Heuristic flags `possible_hallucination` count tracked. |
| 3 | Cost transparency for cloud-model fallbacks | `/requests/cost-quality` table per model. the pilot customer only uses cloud for benchmarks → expect <5% of calls. |
| 4 | Zero external data egress (GraphRAG) | `tcpdump` log on Day 1 + spot-check Day 7. Net traffic = 0 bytes outbound non-local. |

## Pilot timeline

| Day | Milestone | Action |
|-----|-----------|--------|
| 0 (Tue) | Kickoff + first instrumented run | Live on call |
| 1 | Daily ingest > 100 calls | Auto health-check email to Soufian |
| 3 (Fri) | First weekly review | Show Day 0–3 stats, gather friction list |
| 7 | Mid-pilot check-in | Auto-drafted email to the pilot customer with his own numbers |
| 10 (Fri) | Second weekly review | Confirm Day 14 plan, propose pricing |
| 14 | Pilot end → decision call | Convert to paid (Scale tier €2.999/mo or higher) |

## Conversion target

{secondary_workflow} policy compliance + air-gap requirement = **Scale tier (€2.999/mo)** as the floor.
If multi-tenant for their downstream customers comes up → **Enterprise (€5k+/mo)**.

## Risk register (review weekly)

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| SQLite corruption on host crash | Low | Weekly `docker run alpine tar czf` backup script in cron |
| Heuristic-only quality scoring not specific enough for legal/policy domain | Medium | If raised, propose Day-14 add-on: domain-specific eval rubric |
| Ollama OOM during spike → trace partials | Medium | Worker queue holds max 1000; surplus dropped with warn log — recoverable |
| the pilot customer's team grows mid-pilot, second user needs access | Low | Generate additional API key; same dashboard for both |

## Communication

- **Primary:** Tue / Fri call slots
- **Async:** Email Soufian directly. No Slack.
- **Pilot mailbox:** soufian.azzaoui48@gmail.com (replies < 4h CET working hours)

## After Day 14 — handover doc deliverables (if convert)

- Signed pilot summary (numbers from his own dashboard)
- Pricing memo (Scale or Enterprise)
- 12-month contract draft
- Day-30 onboarding plan
