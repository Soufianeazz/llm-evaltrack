# AgentLens Security One-Pager (v1)

Stand: 2026-05-02
Audience: IT, InfoSec, Procurement
Owner: Security + Solutions Engineering

## 1. Product and Data Scope
AgentLens is an LLM observability platform that captures request/response telemetry, quality signals, and trace data to improve reliability, cost control, and incident debugging.

Processed data may include:
- prompt/input/output content
- model and token metadata
- cost and quality metrics
- trace and span execution details

## 2. Core Security Controls

### Authentication and Access
- API-key based access control for ingest and read paths.
- Admin-only endpoints protected via admin token.
- RBAC MVP scope defined as `Admin`, `Analyst`, `Read-only` (implementation track active).

### Transport and Hardening
- TLS required for hosted traffic.
- Security headers enabled (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).
- Request body size limit enabled (256 KB) to reduce abuse surface.

### Data Governance
- Export controls: `/compliance/export` (JSON/CSV).
- Retention controls: `/compliance/retention`, `/compliance/retention/run`.
- Deletion controls: single and bulk delete endpoints.
- Compliance actions recorded in audit log.

## 3. Operational Security and Reliability
- Health endpoints: `/healthz`, `/readyz`, `/health`.
- Internal alerting baseline via scheduled health probe workflow and webhook.
- Backup/restore process documented with RPO/RTO targets.
- Restore drill executed and verified by integrity and record-count checks.
- Incident runbook defines severity, escalation, and communication templates.

## 4. Key Management and Auditability
- API key creation/deactivation actions are audit-logged.
- Rotation endpoint supports:
  - scheduled rotations with grace period
  - emergency rotations without grace period
- Rotation lifecycle events are persisted in audit logs.

## 5. Privacy and Compliance
- AVV/DPA package, SLA draft, and security FAQ are available in procurement pack.
- Subprocessor list is published and linked with purpose and region context.
- PII handling policy defines minimization, masking guidance, and retention/export/delete workflows.

## 6. Current Maturity and Roadmap
- Completed: foundation controls for compliance workflows, audit trail basics, and operational recovery proof.
- In progress: full RBAC enforcement and SSO path decision (OIDC/SAML).
- Planned: deeper tenant/project model and expanded admin action auditing.

## 7. Security Contact
- Vulnerability reporting: `security@agentlens.one`
- Process and triage SLAs: `enterprise/VULNERABILITY_DISCLOSURE_PROCESS.md`
