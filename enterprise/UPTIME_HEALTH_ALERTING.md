# Uptime, Health Endpoints and Internal Alerting

Stand: 2026-05-02
Owner: Engineering
Status: v1

## 1. Health Endpoints
- `GET /healthz`
  - Liveness check (process up)
- `GET /readyz`
  - Readiness check (database reachable)
- `GET /health`
  - Detailed internal health payload including database latency

## 2. Internal Alerting
- Scheduled health probe workflow:
  - `.github/workflows/uptime-health-alert.yml`
- Default check target:
  - `https://www.agentlens.one/healthz`
- Optional override:
  - GitHub secret `HEALTHCHECK_URL`
- Alert destination:
  - GitHub secret `INTERNAL_ALERT_WEBHOOK_URL`
  - Triggered on failed health checks

## 3. Suggested Operations Baseline
- Probe interval: every 10 minutes.
- Alert channel: Slack/Teams webhook.
- Escalation path:
  - On 2 consecutive failures, trigger incident triage.

## 4. Verification
- Health endpoints return `200` when service and DB are healthy.
- Failed checks in the workflow produce a failed run and optional webhook alert.
