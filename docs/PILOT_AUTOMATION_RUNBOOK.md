# Pilot Automation Runbook

## Objective
Run a 14-day customer pilot with minimal manual intervention:
- Access package generation
- Automatic smoke checks
- Continuous health/API monitoring
- Alerting on failure

## 1) One-command setup

Required env:
- `ADMIN_TOKEN`
- optional: `AGENTLENS_BASE_URL` (defaults to `https://www.agentlens.one`)

Run:

```bash
python scripts/setup_pilot_customer.py --customer "Bibin Prathap" --contact-email "bibin@company.com"
```

Outputs:
- New pilot API key
- Smoke validation result
- Guardian one-shot result
- Access package markdown in `enterprise/`

## 2) Continuous background monitor

Run in foreground:

```bash
export AGENTLENS_BASE_URL="https://www.agentlens.one"
export PILOT_ALERT_WEBHOOK_URL="<optional_slack_or_teams_webhook>"
python scripts/pilot_guardian.py --api-key "<pilot_key>" --customer "Bibin" --interval-sec 300
```

Run as Linux service:

1. Copy template:
   - `scripts/pilot_guardian.service.example` -> `/etc/systemd/system/pilot_guardian.service`
2. Replace `<pilot_key>` and optional webhook.
3. Start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pilot_guardian.service
sudo systemctl status pilot_guardian.service
```

## 3) What is monitored

- `GET /healthz`
- `GET /readyz`
- `GET /requests/stats`
- `GET /debug/requests?limit=5`
- `GET /traces?limit=5`
- `GET /compliance/audit-log?limit=5`
- optional E2E:
  - `POST /ingest`
  - `POST /traces`
  - `POST /traces/{id}/spans`
  - `POST /traces/{id}/spans/{span}/end`
  - `POST /traces/{id}/end`
  - `GET /traces/{id}`

## 4) Air-gapped guidance

For strict self-hosted customer workflows:
- keep runtime without `ANTHROPIC_API_KEY`
- keep `DEMO_REQUEST_WEBHOOK_URL` empty
- keep `SIGNUP_NOTIFY_WEBHOOK_URL` empty
- keep `BILLING_EVENT_WEBHOOK_URL` empty
- keep `RESEND_API_KEY` empty
- enforce network egress policy at infrastructure layer

