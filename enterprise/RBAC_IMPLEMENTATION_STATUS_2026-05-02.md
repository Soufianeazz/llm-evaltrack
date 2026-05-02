# RBAC Implementation Status

Stand: 2026-05-02
Owner: Engineering
Status: MVP live

## 1. Implemented Roles
- `admin`
- `analyst`
- `read_only`

## 2. Key Management Support
- API keys now carry role metadata (`api_keys.role`).
- Admin API supports:
  - key creation with role
  - role updates
  - rotation and deactivation with audit events

## 3. Enforced Permissions (MVP)
- `read_only` is blocked from write operations:
  - `POST /ingest`
  - trace write endpoints (`POST /traces`, `POST /traces/{id}/end`, span writes)
- Export and audit access are limited to:
  - `admin`, `analyst`

## 4. Remaining Hardening
- Move admin-token-only actions toward unified tenant-scoped RBAC model.
- Introduce explicit `tenant_id` / `project_id` for stronger multi-tenant isolation.
