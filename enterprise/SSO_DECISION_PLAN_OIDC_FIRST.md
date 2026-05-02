# SSO Decision Plan (OIDC First)

Stand: 2026-05-02
Owner: Product + Engineering + Security
Status: Decision recorded

## Decision
- Primary SSO implementation path: **OIDC first**.
- SAML remains a secondary track for later enterprise compatibility expansion.

## Why OIDC First
- Faster integration path for common enterprise IdPs (Okta, Entra ID, Google Workspace).
- Lower implementation complexity for MVP compared to full SAML stack.
- Better fit with modern API and token-based architecture.

## Scope v1
- Login via OIDC authorization code flow with PKCE.
- Mapping IdP groups/claims to RBAC roles (`admin`, `analyst`, `read_only`).
- Session issuance and logout support.

## Rollout Plan
1. Provider abstraction + configuration model.
2. One production provider integration (recommended: Entra ID or Okta).
3. Role mapping tests and fallback access controls.
4. Security validation and pilot onboarding guide.

## Risks
- Claim mapping inconsistencies across providers.
- Tenant-specific IdP onboarding effort.
- Need for explicit tenant/project model alignment.

## Success Criteria
- At least one enterprise tenant signs in via OIDC in production.
- Role mapping works end-to-end with audit traceability.
