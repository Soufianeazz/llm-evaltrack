# SLA Draft v1

Stand: 2026-05-02
Owner: Legal + Engineering
Status: Draft (for procurement review)

## 1. Scope
- This SLA applies to the managed AgentLens hosted service.
- Self-hosted deployments are excluded unless separately contracted.

## 2. Service Commitment (Draft)
- Monthly availability target: 99.9% for production API and core dashboard endpoints.
- Measurement window: calendar month (UTC).
- Planned maintenance excluded if announced at least 48 hours in advance.

## 3. Severity and Initial Response Times
- Sev 1 (critical outage or data exposure risk): initial response <= 1 hour.
- Sev 2 (major degradation): initial response <= 4 hours.
- Sev 3 (minor degradation): initial response <= 1 business day.
- Sev 4 (questions/low impact): initial response <= 2 business days.

## 4. Support Coverage (Draft)
- Standard: Monday-Friday, 09:00-18:00 CET/CEST.
- Sev 1 emergency escalation: 24/7 best effort (for enterprise plans with on-call addendum).

## 5. Incident Communication
- Sev 1: first customer notice within 60 minutes after confirmation.
- Sev 2: first customer notice within 4 hours after confirmation.
- Update cadence during active incident:
  - Sev 1: every 60 minutes
  - Sev 2: every 4 hours

## 6. Backup and Recovery Targets
- RPO target: <= 24 hours.
- RTO target: <= 60 minutes.
- Backup/restore process reference:
  - `enterprise/BACKUP_RESTORE_PROCESS.md`

## 7. Security and Compliance References
- AVV/DPA outline:
  - `enterprise/AVV_DPA_OUTLINE.md`
- Subprocessor and data flow list:
  - `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`
- Security FAQ:
  - `enterprise/SECURITY_FAQ_V1.md`

## 8. Service Credits (Draft placeholders)
- Availability 99.0% to 99.89%: 10% monthly service credit.
- Availability 95.0% to 98.99%: 25% monthly service credit.
- Availability <95.0%: 50% monthly service credit.
- Credits are capped at the monthly recurring fee for the affected service month.

## 9. Customer Responsibilities
- Customer secures own application-layer secrets and end-user access controls.
- Customer reports incidents promptly via agreed support channel.
- Customer follows API usage limits and fair-use requirements.

## 10. Exclusions
- Force majeure events.
- Customer-side network or infrastructure issues.
- Misconfiguration by customer in self-managed integrations.
- Third-party provider outages outside direct control.

## 11. Open Items for final contract
- Final support timezone and business-hour definition.
- Exact credit claim process and deadline.
- Enterprise plan differentiation (Starter/Team/Scale/Custom).
