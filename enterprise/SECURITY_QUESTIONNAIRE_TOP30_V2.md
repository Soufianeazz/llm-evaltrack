# Security Questionnaire Top 30 v2

Stand: 2026-05-02
Owner: Founder + Engineering
Version: 2.0
Status: Customer-shareable baseline

## Purpose
This document provides concise standard responses to the 30 most common enterprise security questionnaire prompts.

## Governance and Program

### Q1. Do you maintain a formal security policy?
A1. Yes. A public baseline security policy is available at `/security` and mapped to internal enterprise controls documentation.

### Q2. Is there a dedicated security contact channel?
A2. Yes. Security inquiries and vulnerability reports are handled via `security@agentlens.one`.

### Q3. Do you run an incident response process?
A3. Yes. Incident severity classification, escalation, and communication workflow are documented in `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`.

### Q4. Do you provide a vulnerability disclosure process?
A4. Yes. Intake and triage flow are documented in `enterprise/VULNERABILITY_DISCLOSURE_PROCESS.md`.

### Q5. How often are security controls reviewed?
A5. Controls are reviewed and updated through a versioned enterprise readiness process tracked in `ENTERPRISE_READINESS_CHECKLIST_2026-05-02.md`.

## Identity and Access

### Q6. Is access control role-based?
A6. Yes. Baseline roles are `admin`, `analyst`, and `read_only`.

### Q7. How is API access authenticated?
A7. API access requires valid API key credentials through supported request authentication patterns.

### Q8. Are privileged actions tracked?
A8. Yes. Governance-critical admin and compliance operations are audit logged.

### Q9. Do you support SSO?
A9. SSO direction is OIDC-first with implementation planning documented in `enterprise/SSO_DECISION_PLAN_OIDC_FIRST.md`.

### Q10. Is least-privilege enforced?
A10. Role boundaries are defined in the RBAC model and used as the enforcement baseline.

## Encryption and Platform Security

### Q11. Is data encrypted in transit?
A11. Yes. TLS is required for hosted service traffic.

### Q12. Are security headers enforced?
A12. Yes. Response headers include CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy.

### Q13. Is backup storage encrypted?
A13. Backup storage is expected to use encryption-at-rest controls per backup/restore policy.

### Q14. Are request abuse protections in place?
A14. Request-size limits and other defensive controls are applied to relevant ingestion paths.

### Q15. Do you expose health endpoints for monitoring?
A15. Yes. `/healthz`, `/readyz`, and `/health` are available.

## Logging, Monitoring, and Audit

### Q16. Are customer governance actions auditable?
A16. Yes. Export, delete, and retention-related governance operations are represented in audit events.

### Q17. Can audit logs be exported?
A17. Yes. Audit export supports CSV and JSON with filterable ranges.

### Q18. Is operational tracing available?
A18. Yes. Trace records support debugging and incident reconstruction.

### Q19. Is uptime monitored?
A19. Yes. Health monitoring and uptime alert workflows are implemented.

### Q20. Are incident updates provided during major events?
A20. Yes. Communication cadence for major incidents follows SLA-defined severity expectations.

## Data Processing and Privacy

### Q21. How is personal data handled?
A21. PII handling baseline is documented in `enterprise/PII_HANDLING_POLICY.md`.

### Q22. Can customers control retention?
A22. Yes. Retention controls are available through compliance workflows.

### Q23. Can customers request deletion/export?
A23. Yes. Data governance flows support export and deletion workflows.

### Q24. Are sub-processors disclosed?
A24. Yes. Public register available at `/subprocessors`.

### Q25. Is data flow documentation available?
A25. Yes. Detailed flow notes are documented in `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`.

## Reliability and Business Continuity

### Q26. What are recovery targets?
A26. Current baseline targets are RPO <= 24h and RTO <= 60m.

### Q27. Is restore capability tested?
A27. Yes. Restore drill protocol and evidence are documented in `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`.

### Q28. Is an SLA available?
A28. Yes. Public SLA summary is available at `/sla` with baseline commitments documented in `enterprise/SLA_V2_FINAL.md`.

## Contracting and Procurement

### Q29. Do you provide a legal/security package for procurement?
A29. Yes. Legal pack is published at `/legal-pack` and includes DPA/AVV, Security Annex, Data Processing Annex, and SLA references.

### Q30. Can responses be tailored to customer questionnaire formats?
A30. Yes. This Top-30 baseline can be adapted to customer-specific templates during security/legal review.

## Contact
- Security intake: security@agentlens.one
- Commercial/legal review: contact@agentlens.one
