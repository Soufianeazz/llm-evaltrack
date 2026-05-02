# Tenant and Project Separation

Stand: 2026-05-02
Owner: Engineering + Security
Status: v1

## 1. Separation Model
- Runtime data access is scoped by API key context.
- Requests, evaluations, and traces are filtered by `api_key` on read endpoints.
- Cross-key data reads are denied by query-level constraints.

## 2. Endpoints with Key-Scoped Access
- `/requests/*`
- `/debug/requests*`
- `/traces*`
- `/ingest`

These endpoints require a valid active API key and operate within that key context.

## 3. Admin-Scope Actions
- Admin endpoints (`/admin/*`) require `ADMIN_TOKEN`.
- Compliance destructive actions require admin authorization.
- Key lifecycle actions are audit-logged.

## 4. UI Labeling
- UI pages include explicit scope indicator:
  - "Data Scope: API-key isolated project context"
- Applied to dashboard, debugger, traces, and compliance views.

## 5. Residual Risks and Next Steps
- Current model is key-scoped; enterprise tenants may require explicit tenant and project IDs in schema.
- Recommended next step:
  - Introduce first-class `tenant_id` and `project_id` fields
  - Enforce RBAC role checks bound to tenant/project
