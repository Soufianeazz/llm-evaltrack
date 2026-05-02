# RBAC MVP Scope (Admin / Analyst / Read-only)

Stand: 2026-05-02
Owner: Product + Engineering + Security
Status: Scope fixed (MVP)

## 1. Ziel
- Minimal belastbares RBAC fuer Enterprise-Piloten definieren.
- Rollen: `Admin`, `Analyst`, `Read-only`.
- Fokus auf API/Compliance/Audit/Billing-nahe Aktionen.

## 2. Rollenbeschreibung
- `Admin`
  - Vollzugriff auf Tenant/Projekt-Einstellungen, API-Keys, Retention, Loeschaktionen und Exporte.
  - Darf sicherheits- und kostenrelevante Konfiguration aendern.
- `Analyst`
  - Operativer Zugriff auf Dashboards, Debug, Traces, Exporte.
  - Kein Zugriff auf sicherheitskritische Admin-Aktionen (Key-Management, Delete, Retention-Policy).
- `Read-only`
  - Lesender Zugriff auf Dashboards und Observability-Ansichten.
  - Keine Konfigurations- oder Export-/Delete-Aktionen.

## 3. Rechte-Matrix (MVP)

| Bereich | Endpoint/Action | Admin | Analyst | Read-only |
|---|---|---:|---:|---:|
| Ingest | `POST /ingest` (mit API-Key des Workloads) | Allow | Allow | Allow |
| Dashboard KPIs | `GET /requests/*` | Allow | Allow | Allow |
| Prompt Debug | `GET /debug/requests*` | Allow | Allow | Allow |
| Traces lesen | `GET /traces`, `GET /traces/{id}` | Allow | Allow | Allow |
| Traces schreiben | `POST /traces*` | Allow | Allow | Deny |
| Budget Alert lesen | `GET /alerts/budget` | Allow | Allow | Allow |
| Budget Alert aendern | `POST/DELETE /alerts/budget` | Allow | Deny | Deny |
| Compliance Export | `GET /compliance/export` | Allow | Allow | Deny |
| Retention ansehen | `GET /compliance/retention` | Allow | Allow | Allow |
| Retention aendern | `POST /compliance/retention`, `POST /compliance/retention/run` | Allow | Deny | Deny |
| Loeschung | `DELETE /compliance/requests*` | Allow | Deny | Deny |
| Audit Log lesen | `GET /compliance/audit-log` | Allow | Allow | Deny |
| API-Key Management | `POST/GET/DELETE /admin/api-keys*` | Allow | Deny | Deny |
| Demo Admin/Exports | `GET /demo-request*` (admin-token geschuetzt) | Allow | Deny | Deny |
| Billing Checkout | `GET /billing/checkout/{plan}` | Allow | Allow | Allow |

## 4. Tenant/Projekt-Prinzipien
- Rollen sind tenant-scoped, nicht global.
- Jeder API-Key ist genau einem Tenant/Projekt zugeordnet.
- Cross-tenant Zugriff ist immer `Deny`.

## 5. Audit-Pflichtige Aktionen (MVP)
- API-Key erstellt/deaktiviert/rotiert
- Retention-Policy geaendert oder manuell ausgefuehrt
- Datenexport ausgefuehrt
- Loeschaktionen ausgefuehrt (einzeln/bulk)
- Budget Alerts geaendert

## 6. Implementierungsumfang fuer MVP
- Auth-Layer erweitert um:
  - User/Service Principal mit Rolle
  - Tenant-ID Kontext
- Enforcement:
  - RBAC-Checks zentral vor Route-Handlern
- Migration:
  - Mapping existierender Admin-Token-Flows auf Rolle `Admin`
- UI:
  - Sichtbarkeit von Admin-Aktionen role-aware ausblenden

## 7. Akzeptanzkriterien
- Jede geschuetzte Aktion liefert bei fehlender Berechtigung `403`.
- Kein Role Escalation Pfad ueber Query-Parameter/Header.
- Jede admin-kritische Aktion erzeugt Audit-Log-Eintrag.
