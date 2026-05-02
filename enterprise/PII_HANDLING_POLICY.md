# PII Handling Policy

Stand: 2026-05-02
Owner: Security + Compliance
Status: v1

## 1. Scope
- Applies to all payloads processed by AgentLens (`input`, `output`, `prompt`, metadata).
- Covers masking guidance, retention controls, export/delete flows, and operational safeguards.

## 2. Data Minimization Guidance
- Do not send unnecessary personal data in prompts or outputs.
- Prefer pseudonymous IDs over direct identifiers where possible.
- Keep payloads limited to required debugging/evaluation context.

## 3. Masking and Redaction Guidance
- Recommended upstream redaction before calling `/ingest`:
  - email addresses
  - phone numbers
  - government IDs
  - payment/account numbers
- Where full redaction is not possible, mask partial values (for example `u***@domain.com`).

## 4. Retention Controls
- Retention is configurable via `/compliance/retention`.
- Manual retention execution is available via `/compliance/retention/run`.
- Bulk delete by age is available via `/compliance/requests?older_than_days=...`.

## 5. Export and DSAR Support
- Data export is available in JSON/CSV via `/compliance/export`.
- Deletion by specific request ID is available via `/compliance/requests/{request_id}`.
- Compliance actions are logged in `audit_log` for traceability.

## 6. Operational Handling
- Restrict admin token access to least-privilege operators.
- Rotate API keys regularly and on suspected exposure.
- Use incident runbook for any potential PII exposure event.

## 7. Known Limitations (v1)
- Automatic PII detection/masking is not yet built into ingestion path.
- Current protection relies on upstream redaction and governance controls.

## 8. Planned Improvements
- Add optional server-side PII detection hooks.
- Add policy-based masking templates per tenant/project.
- Add explicit data classification tags in metadata.
