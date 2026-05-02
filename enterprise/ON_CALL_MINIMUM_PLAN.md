# On-call Minimum Plan

Stand: 2026-05-02
Owner: Engineering + Founder
Status: v1

## 1. Coverage Model (Minimum)
- Primary on-call:
  - one named engineer per week
- Secondary backup:
  - one escalation contact
- Business-hours baseline with emergency escalation path for Sev1

## 2. Response Targets
- Sev1 page acknowledgment: <= 15 minutes
- Sev2 page acknowledgment: <= 30 minutes
- Sev3/Sev4: next business window

## 3. Alert Ingestion
- Health-check workflow failures
- Internal webhook alerts
- Customer escalation channel

## 4. Escalation Path
1. Primary on-call triages and classifies severity
2. Secondary joins if unresolved in 30 minutes
3. Founder/CTO notified for Sev1 incidents

## 5. Runbook and Communication
- Incident handling follows `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`
- Customer communication cadence follows severity matrix

## 6. Weekly Hygiene
- Rotation schedule confirmed every Friday
- Contact sheet validated weekly
- Post-incident actions reviewed in weekly ops sync
