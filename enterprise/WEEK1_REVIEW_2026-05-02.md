# Week 1 Review (Enterprise Readiness)

Stand: 2026-05-02
Owner: Founder + Engineering
Scope: Tag 1 bis Tag 5

## 1. Completed This Week
- AVV/DPA outline created.
- Security FAQ structure and v1 FAQ created.
- Incident runbook template created.
- Subprocessor list + data flow v1 created.
- Backup/restore process documented.
- RBAC MVP scope defined with role matrix.
- API key rotation process + audit event schema defined.
- SLA draft v1 created.
- Procurement pack v1 created.
- Enterprise demo script (20-30 min, compliance/trust focused) created.
- Restore drill executed and documented.

## 2. Current Gaps
- DPA/AVV and SLA are still draft-level and need legal redline/final wording.
- Subprocessor list needs final public publication with verified legal entities/regions.
- Vulnerability disclosure process (mailbox + triage SLA + disclosure text) not finalized.
- RBAC and rotation audit events are documented but not fully enforced in runtime code yet.
- SSO decision and implementation not yet started.

## 3. Blockers / Risks
- Legal dependency: final contract language requires legal review capacity.
- Security operations dependency: no finalized vulnerability intake channel yet.
- Product hardening risk: enterprise prospects may request live RBAC enforcement before pilot signature.
- Process risk: without periodic restore drills and metrics tracking, reliability claims can drift.

## 4. Priority Plan for Next 2 Weeks

## Week 2 priorities
1. Finalize vulnerability process and publish security intake/disclosure page.
2. Add first RBAC enforcement layer for admin-critical actions.
3. Implement audit-log entries for API key create/deactivate/rotation events.
4. Publish subprocessor page (customer-facing URL) with change-notice policy.

## Week 3 priorities
1. Convert SLA draft to negotiable template with legal review comments resolved.
2. Convert DPA/AVV outline into redline-ready template package.
3. Define and start SSO decision track (OIDC vs SAML) with implementation plan.
4. Prepare standard security questionnaire response pack (top 30 questions).

## 5. Decision Log
- Keep SQLite-based backup/restore process for MVP with monthly restore drill cadence.
- Treat procurement package as living artifact, versioned per week.
- Use documented RBAC matrix as enforcement contract for implementation phase.

## 6. Success Criteria for End of Next 2 Weeks
- Legal/security package moves from draft to customer-shareable v2.
- Runtime includes first enforceable governance controls (RBAC + audit entries).
- Security intake and subprocessor transparency are publicly referenceable.
