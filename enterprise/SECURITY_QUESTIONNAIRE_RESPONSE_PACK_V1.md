# Security Questionnaire Response Pack v1

Stand: 2026-05-02
Owner: Founder + Engineering
Version: 1.0

## Purpose
This document provides standard security questionnaire answers for enterprise buyers evaluating AgentLens.

## 1) Company and Service
- Legal Name: AgentLens (operated by founding team; legal entity details shared in contracting package).
- Product Scope: LLM observability platform with quality scoring, hallucination detection, cost tracking, and agent debugging.
- Delivery Models: Managed hosted deployment and self-hosted model.

## 2) Security Program
- Security contact: security@agentlens.one
- Vulnerability intake process: documented in `enterprise/VULNERABILITY_DISCLOSURE_PROCESS.md`.
- Incident process: documented in `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`.
- Security policy page: `/security`

## 3) Access Control
- Minimum role model: `admin`, `analyst`, `read_only`.
- API access: API key required via `X-API-Key` header or `?api_key=` query parameter.
- Governance controls: admin actions and key governance actions are audit-logged.

## 4) Authentication and SSO
- Current baseline: API-key authentication with RBAC controls.
- SSO direction: OIDC-first strategy documented in `enterprise/SSO_DECISION_PLAN_OIDC_FIRST.md`.

## 5) Encryption and Transport
- Transport: TLS required for hosted traffic.
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Backup encryption expectation: encrypted backup storage per backup/restore process.

## 6) Logging and Auditability
- Audit logging for compliance operations (export/delete/retention actions) and governance-critical admin operations.
- Audit export support: CSV and JSON with filterable ranges.
- Operational traces support post-incident analysis and debug workflows.

## 7) Data Governance and Privacy
- PII handling policy documented in `enterprise/PII_HANDLING_POLICY.md`.
- Retention controls and warnings available in compliance UI.
- Data operations supported: export, retention updates, delete workflows with audit entries.

## 8) Subprocessors and Data Residency
- Public subprocessor register: `/subprocessors`
- Detailed data-flow notes: `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`
- Region behavior: depends on configured project/account region and deployment setup.

## 9) Reliability and Business Continuity
- Health endpoints: `/healthz`, `/readyz`, `/health`
- Uptime alerting: `.github/workflows/uptime-health-alert.yml`
- Backup/restore process: `enterprise/BACKUP_RESTORE_PROCESS.md`
- Restore drill protocol: `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`

## 10) Secure Development and Change Control
- Core controls are versioned in GitHub with pull request review flow.
- Change transparency is provided via repository history and documented runbooks/processes.
- Planned hardening: change-management policy formalization in Phase 3 checklist.

## 11) Contract and Legal Pack
- Procurement package: `enterprise/PROCUREMENT_PACK_V1.md`
- DPA/AVV template: `enterprise/AVV_DPA_TEMPLATE_V1_FINAL.md`
- SLA draft: `enterprise/SLA_DRAFT_V1.md`

## 12) Standard Response Notes for Buyers
- This pack is a baseline response set and may be expanded per customer questionnaire format.
- Customer-specific security commitments are finalized in signed contractual documents.
- For formal reviews or custom questionnaire sessions: contact@agentlens.one
