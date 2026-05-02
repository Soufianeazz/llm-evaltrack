# Security Annex v1 Final

Stand: 2026-05-02
Owner: Legal + Engineering
Status: Final baseline for enterprise contracting

## 1. Purpose
This Security Annex defines the baseline technical and organizational security controls for AgentLens managed hosted service.

## 2. Security Governance
- Dedicated security contact channel: security@agentlens.one.
- Vulnerability intake and triage process is documented in `enterprise/VULNERABILITY_DISCLOSURE_PROCESS.md`.
- Incident handling baseline is documented in `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`.

## 3. Access Control and Identity
- Role baseline: `admin`, `analyst`, `read_only`.
- API access requires valid API credentials.
- Governance-critical operations are audit logged.
- SSO strategy and implementation direction is documented in `enterprise/SSO_DECISION_PLAN_OIDC_FIRST.md`.

## 4. Infrastructure and Network Security
- TLS is required for hosted traffic.
- Security response headers are enforced on platform responses.
- Request-size limits are enforced on ingest entry points.
- Uptime and readiness endpoints are available for operational monitoring.

## 5. Data Security Controls
- Data lifecycle controls include export, retention, and deletion workflows.
- Compliance operations are represented in audit logging flows.
- PII handling baseline is documented in `enterprise/PII_HANDLING_POLICY.md`.

## 6. Logging and Monitoring
- Audit events cover governance and compliance-relevant operations.
- Audit export supports CSV/JSON for evidence workflows.
- Operational traces support debugging and post-incident analysis.

## 7. Business Continuity and Recovery
- Backup and restore process is defined in `enterprise/BACKUP_RESTORE_PROCESS.md`.
- Recovery objectives baseline:
  - RPO <= 24 hours
  - RTO <= 60 minutes
- Restore drill protocol reference: `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`.

## 8. Subprocessors and Third Parties
- Public subprocessor register: `/subprocessors`
- Detailed data flow and purpose notes: `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`
- Third-party services are categorized as required core or optional by feature usage.

## 9. Incident Communication Commitments
- Incident communication cadence follows SLA severity levels.
- Sev 1 and Sev 2 incidents include customer-facing updates and post-incident summary.
- Commercial response commitments are defined in `enterprise/SLA_V2_FINAL.md`.

## 10. Control Improvement
- Controls are versioned and improved through documented checklist phases.
- Additional hardening activities (for example pentest cycle, change management formalization) are tracked in enterprise readiness plan.

## 11. Contract Note
This annex is a baseline security schedule and may be extended through customer-specific contractual addenda.
