# SLO and Error Budget Draft

Stand: 2026-05-02
Owner: Engineering
Status: v1

## 1. Service Level Objective
- Availability SLO (monthly): 99.9%
- Scope:
  - API availability for key endpoints (`/ingest`, `/requests/stats`, `/traces`)
  - Excludes scheduled maintenance windows announced in advance

## 2. Error Budget
- Monthly downtime budget at 99.9%:
  - 43 minutes, 49 seconds
- Burn policy:
  - >25% budget burn in first week triggers reliability review
  - >50% budget burn in first two weeks triggers release hardening mode

## 3. Measurement
- Source signals:
  - Health check workflow results
  - Synthetic probes to `healthz` and selected API endpoints
- Aggregation:
  - Daily rollup
  - Monthly SLO report

## 4. Alert Thresholds
- Immediate alert:
  - 2 consecutive failed health checks
- Escalation:
  - 4 consecutive failures => incident process (Sev2+ triage)

## 5. Weekly Review Inputs
- SLO attainment trend
- Error budget consumed
- Top outage contributors
- Action items and owner tracking
