# API Key Rotation Process and Audit Events

Stand: 2026-05-02
Owner: Security + Platform Engineering
Status: v1

## 1. Ziel
- Sichere, nachweisbare Rotation von API-Keys ohne unnoetigen Downtime-Risiko.
- Vollstaendige Nachvollziehbarkeit ueber Audit-Events.

## 2. Wann rotieren
- Planmaessig: alle 90 Tage (Enterprise baseline)
- Sofortrotation bei:
  - Verdacht auf Key-Leak
  - Offboarding kritischer Mitarbeitender
  - Unautorisierte Nutzungsmuster

## 3. Rotationstypen
- `Scheduled Rotation`
  - Regelmaessige Erneuerung.
- `Emergency Rotation`
  - Beschleunigter Prozess, alte Keys schnellstmoeglich deaktivieren.

## 4. Standardablauf (Scheduled Rotation)
1. Vorbereitung
  - Betroffenen Tenant/Projekt-Key identifizieren.
  - Verantwortliche Person (`actor`) benennen.
2. Neuen Key erstellen
  - Neuer Key mit gleichem Scope/Plan.
3. Dual-Key-Phase starten (Grace Window)
  - Alter + neuer Key parallel aktiv.
  - Ziel: Client-Config sauber umstellen.
4. Traffic validieren
  - Pruefen, dass Ingest/Traces ueber neuen Key laufen.
5. Alten Key deaktivieren
  - Deaktivierung nach erfolgreicher Umstellung.
6. Abschluss
  - Ticket dokumentieren und Rotation als abgeschlossen markieren.

Empfohlenes Grace Window: 24 Stunden (anpassbar pro Enterprise-Kunde).

## 5. Emergency Rotation Ablauf
1. Neuen Key sofort erstellen.
2. Alten Key sofort deaktivieren (kein Grace Window, falls Leak verifiziert).
3. Kundenkontakt/Owner sofort informieren.
4. Erhoehte Beobachtung fuer 24 Stunden (invalid key errors, traffic anomalies).

## 6. Audit Event Schema (MVP)
- Event sink: `audit_log`
- Pflichtfelder im Detail-JSON/Text:
  - `event_type`
  - `timestamp`
  - `actor_id` (oder `system`)
  - `tenant_id` / `project_id` (falls vorhanden)
  - `api_key_prefix` (nur Prefix, nie voller Key)
  - `reason` (`scheduled`, `emergency`, `manual`)
  - `rotation_id` (korreliert alle Schritte)
  - `status` (`started`, `succeeded`, `failed`)

## 7. Event-Typen
- `api_key.rotation_started`
- `api_key.created`
- `api_key.rotation_grace_started`
- `api_key.rotation_validated`
- `api_key.deactivated`
- `api_key.rotation_completed`
- `api_key.rotation_failed`

## 8. Beispiel-Audit-Events

```json
{
  "event_type": "api_key.rotation_started",
  "actor_id": "admin_user_42",
  "tenant_id": "tenant_acme",
  "api_key_prefix": "al_abcd",
  "reason": "scheduled",
  "rotation_id": "rot_20260502_001",
  "status": "started"
}
```

```json
{
  "event_type": "api_key.deactivated",
  "actor_id": "admin_user_42",
  "tenant_id": "tenant_acme",
  "api_key_prefix": "al_wxyz",
  "reason": "scheduled",
  "rotation_id": "rot_20260502_001",
  "status": "succeeded"
}
```

## 9. Sicherheitsregeln
- Niemals vollen API-Key in Logs, Audit oder UI anzeigen.
- Key-Anzeige im UI nur maskiert (z. B. `al_abcd...wxyz`).
- Rotation darf nur durch `Admin` Rolle ausgeloest werden.

## 10. Operative KPIs
- Rotationsabdeckung: Anteil Keys mit Rotation <= 90 Tage
- Median Rotationsdauer: `rotation_started` bis `rotation_completed`
- Fehlerquote bei Rotation: Anteil `rotation_failed`
- Anteil Emergency Rotations pro Monat

## 11. Umsetzungshinweise im aktuellen Code
- Bestehende Endpunkte:
  - `POST /admin/api-keys` (create)
  - `DELETE /admin/api-keys/{key}` (deactivate)
- Erweiterungen fuer v1.1:
  - `POST /admin/api-keys/{key}/rotate` (orchestrierter Ablauf)
  - Audit-Log-Eintraege bei create/deactivate/rotate
  - Optionale Grace-Window-Validierung (Usage-Signal)
