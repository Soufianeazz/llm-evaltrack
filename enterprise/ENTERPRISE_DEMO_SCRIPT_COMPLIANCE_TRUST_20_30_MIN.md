# Enterprise Demo Script (20-30 min)

Stand: 2026-05-02
Owner: Sales Engineering
Status: v1

## 1. Demo objective
- Show that AgentLens is not only useful for LLM quality and cost, but also procurement-ready on compliance, auditability, and operations basics.

## 2. Audience
- CTO / VP Engineering
- Security / InfoSec reviewer
- Procurement stakeholder

## 3. Timing plan (25 min default)
- 0:00-2:00: Context and success criteria
- 2:00-8:00: Product value (quality, cost, traces)
- 8:00-15:00: Compliance and audit controls
- 15:00-21:00: Governance (RBAC, key rotation, retention)
- 21:00-25:00: Procurement pack walk-through + next steps

## 4. Pre-demo checklist
- Demo API key active (`al_demo_agentlens` or tenant key).
- Dashboard reachable.
- Example traces available.
- Compliance endpoints reachable.
- Procurement docs open locally in `enterprise/`.

## 5. Talk track and click path

## 5.1 Opening (2 min)
- "Today we will validate three enterprise questions:  
  1) Can we trust the data controls?  
  2) Can we audit critical actions?  
  3) Is there a concrete procurement package?"

## 5.2 Core observability value (6 min)
- Show dashboard KPIs (`/requests/stats` view in UI).
- Show worst responses and root-cause patterns.
- Show trace waterfall (`/traces`) to highlight per-step visibility.
- Message: "Operational transparency is immediate, not post-hoc."

## 5.3 Compliance and audit controls (7 min)
- Open compliance page (`/compliance.html`).
- Demonstrate:
  - export capability (`/compliance/export`)
  - retention policy view (`/compliance/retention`)
  - audit log (`/compliance/audit-log`)
- Message: "Data lifecycle actions are controllable and inspectable."

## 5.4 Governance trust block (6 min)
- Present RBAC scope doc:
  - `enterprise/RBAC_MVP_SCOPE.md`
- Present API key rotation process + audit events:
  - `enterprise/API_KEY_ROTATION_PROCESS_AND_AUDIT_EVENTS.md`
- Highlight:
  - Admin-only key operations
  - planned 90-day rotation baseline
  - audit event schema for each rotation phase

## 5.5 Procurement readiness close (4 min)
- Open package index:
  - `enterprise/PROCUREMENT_PACK_V1.md`
- Walk through:
  - AVV/DPA outline
  - SLA draft
  - Security FAQ
  - Subprocessor/data flow document
- Message: "We can start legal/security review immediately, not after pilot."

## 6. Objection handling snippets
- "Do you support GDPR workflows?"
  - "Yes, export/retention/delete endpoints and audit logging are already in place."
- "How do you manage incident communication?"
  - "Runbook defines severity, escalation, and customer update templates."
- "What if an API key is leaked?"
  - "Rotation process supports emergency replacement and documented audit trail."

## 7. Success criteria for the call
- Security reviewer accepts FAQ + subprocessor draft as review baseline.
- Procurement accepts AVV/SLA drafts for redlining.
- Technical champion agrees on pilot scope and timeline.

## 8. Follow-up package (send within 24h)
- `enterprise/PROCUREMENT_PACK_V1.md`
- `enterprise/ENTERPRISE_DEMO_SCRIPT_COMPLIANCE_TRUST_20_30_MIN.md`
- Any customer-specific notes from Q&A
