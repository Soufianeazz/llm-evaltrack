# SLA v2 Final (Customer-Shareable)

Stand: 2026-05-02
Owner: Legal + Engineering
Status: Customer-shareable v2 baseline

## 1. Scope
- This SLA applies to the managed AgentLens hosted service.
- Self-hosted deployments are excluded unless explicitly covered in a separate contract addendum.

## 2. Service Availability Commitment
- Monthly availability target: 99.9% for production API and core dashboard endpoints.
- Measurement window: calendar month (UTC).
- Excluded from downtime calculation:
  - Planned maintenance announced at least 48 hours in advance.
  - Force majeure events.
  - Customer-side incidents or misconfiguration.

## 3. Severity Classification and Initial Response Times
- Sev 1 (critical outage or suspected security impact): initial response <= 1 hour (24/7).
- Sev 2 (major degradation affecting key workflows): initial response <= 4 hours.
- Sev 3 (partial degradation or non-critical defect): initial response <= 1 business day.
- Sev 4 (low impact question/request): initial response <= 2 business days.

## 4. Support Coverage
- Standard support hours: Monday-Friday, 09:00-18:00 CET/CEST (excluding public holidays in Germany).
- Sev 1 emergency path: 24/7 on-call escalation.

## 5. Incident Communication Commitments
- Sev 1: first customer communication within 60 minutes after confirmation.
- Sev 2: first customer communication within 4 hours after confirmation.
- Update cadence during active incident:
  - Sev 1: every 60 minutes
  - Sev 2: every 4 hours
- Post-incident summary (RCA-style) is provided for Sev 1 and Sev 2 incidents.

## 6. Backup and Recovery Targets
- RPO target: <= 24 hours.
- RTO target: <= 60 minutes.
- Process references:
  - `enterprise/BACKUP_RESTORE_PROCESS.md`
  - `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`

## 7. Service Credits
- 99.0% to 99.89% monthly availability: 10% monthly service credit.
- 95.0% to 98.99% monthly availability: 25% monthly service credit.
- Below 95.0% monthly availability: 50% monthly service credit.
- Credit cap: monthly recurring fee for the affected service month.

## 8. Credit Claim Process
- Customer submits claim within 30 calendar days after the affected month.
- Claim must include account identifier, month, and incident references.
- Approved credits are applied to the next invoice cycle.

## 9. Customer Responsibilities
- Protect customer-side access credentials and secret material.
- Report service incidents promptly through agreed support channels.
- Operate integrations within documented usage and rate limits.

## 10. Security and Compliance References
- Security policy page: `/security`
- Security questionnaire pack: `/security-questionnaire`
- Subprocessor register: `/subprocessors`
- DPA/AVV template: `enterprise/AVV_DPA_TEMPLATE_V1_FINAL.md`

## 11. Contract Notes
- This SLA v2 is the baseline for commercial contracting.
- Customer-specific adjustments (for example higher availability or custom support windows) may be documented in enterprise order forms or addenda.
