# Data Processing Annex v1 Final

Stand: 2026-05-02
Owner: Legal + Engineering
Status: Final baseline for enterprise contracting

## 1. Purpose
This Data Processing Annex defines baseline data processing terms for AgentLens managed hosted service.

## 2. Roles
- Customer acts as data controller for customer-provided operational and application data.
- AgentLens acts as data processor for data processed on behalf of customer.

## 3. Processing Scope
- Service scope: LLM observability telemetry, quality scoring metadata, trace context, and governance event records.
- Processing purpose: platform operation, debugging, quality monitoring, compliance workflows, and service reliability.

## 4. Data Categories (Typical)
- Customer account and workspace metadata.
- Trace metadata and prompt/response context segments (as configured by customer usage patterns).
- Compliance and audit event records.
- Support and operational interaction metadata.

## 5. Data Subjects (Typical)
- Customer team users and administrators.
- End users represented in customer-provided payloads, subject to customer-controlled upstream handling.

## 6. Retention and Deletion
- Retention controls are configurable via compliance workflows.
- Customer may request export and deletion operations through documented flows.
- Retention and delete operations are captured in audit logs where applicable.

## 7. Security Measures (Reference)
- Security baseline controls are defined in `enterprise/SECURITY_ANNEX_V1_FINAL.md`.
- Additional policy references:
  - `enterprise/PII_HANDLING_POLICY.md`
  - `enterprise/SLA_V2_FINAL.md`

## 8. Subprocessors
- Public register: `/subprocessors`
- Detailed notes: `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`
- Subprocessor usage depends on enabled service components and customer configuration.

## 9. International Transfers and Region Behavior
- Region behavior follows configured deployment/account region and hosting setup.
- Customer-specific regional commitments are finalized in executed contract documents.

## 10. Assistance and Data Subject Requests
- Customer-facing governance workflows support export and deletion related operations.
- AgentLens provides reasonable support for controller obligations as specified by contract.

## 11. Breach Notification
- Security incidents are handled via incident process and communication commitments.
- Notification timing and structure follow contractual SLA/security terms.

## 12. Audit and Documentation
- Operational and compliance events are logged for evidentiary support.
- Documentation artifacts are maintained in versioned enterprise controls package.

## 13. Contract Note
This annex is the baseline processing schedule and may be supplemented with customer-specific legal clauses in final agreements.
