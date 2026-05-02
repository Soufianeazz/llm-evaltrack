# Security FAQ v1

Stand: 2026-05-02
Owner: Security + Solutions Engineering
Status: Draft answers for procurement/security review

## 1) Welche Authentifizierung nutzt AgentLens?
AgentLens nutzt API-Keys fuer Ingest- und Trace-nahe API-Zugriffe. Der Key kann als `X-API-Key` Header oder als Query-Parameter uebergeben werden. Ungueltige oder inaktive Keys werden mit `403` abgewiesen.

## 2) Gibt es rollenbasierte Berechtigungen?
Das RBAC-MVP mit `Admin`, `Analyst` und `Read-only` ist als Scope definiert und in Umsetzung. Die Rechte-Matrix liegt in `enterprise/RBAC_MVP_SCOPE.md` und priorisiert Schutz fuer Key-Management, Retention und Delete-Aktionen.

## 3) Wie wird Datenverkehr geschuetzt?
Die Anwendung setzt Security-Header (u. a. `Strict-Transport-Security`, CSP, `X-Frame-Options`, `X-Content-Type-Options`). In Produktion wird TLS fuer Verbindungen zur Plattform vorausgesetzt.

## 4) Wie wird Datenzugriff getrennt?
Datenabfragen in den Dashboard- und Trace-Endpoints sind API-Key-gebunden und filtern auf den jeweiligen Key-Kontext. Das reduziert das Risiko unautorisierter Einsicht zwischen Projekten/Tenants.

## 5) Welche Daten verarbeitet AgentLens?
Verarbeitet werden Prompt-/Response-Inhalte, Modell- und Token-Metadaten, Kostenmetriken, Trace-Spans und Betriebsdaten wie Audit- und Retention-Informationen. Details sind im AVV/DPA-Outline dokumentiert.

## 6) Wie funktionieren Export und Loeschung?
Compliance-Endpunkte unter `/compliance` ermoeglichen Export (JSON/CSV), Einzel- und Bulk-Loeschung sowie Retention-Policy-Steuerung. Relevante Aktionen werden im Audit-Log protokolliert.

## 7) Gibt es Audit-Logs?
Ja. Compliance-relevante Aktionen wie Exporte, Loeschungen und Policy-Aenderungen werden in `audit_log` abgelegt. Fuer API-Key-Rotationen ist ein erweitertes Event-Schema in `enterprise/API_KEY_ROTATION_PROCESS_AND_AUDIT_EVENTS.md` definiert.

## 8) Wie wird Retention umgesetzt?
Retention kann konfiguriert und manuell ausgelost werden (`/compliance/retention`, `/compliance/retention/run`). Die Policy enthaelt Aufbewahrungsdauer, Aktivierungsstatus und Zeitstempel letzter Ausfuehrung.

## 9) Gibt es Schutz gegen Missbrauch der API?
Ja. Es gibt Request-Limits ueber `slowapi` auf zentralen Endpunkten und ein Body-Size-Limit (256 KB) fuer HTTP Requests. Das reduziert Abuse- und DoS-Risiken im MVP.

## 10) Wie ist Incident Response geregelt?
Es existiert ein Incident-Runbook mit Severity-Matrix, Eskalationspfad und Kommunikationsvorlagen. Das Template ist unter `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md` abgelegt.

## 11) Wie ist Backup/Restore organisiert?
Ein schriftlicher Prozess fuer Backup, Restore, Integritaetspruefung und RPO/RTO-Ziele ist vorhanden. Referenz: `enterprise/BACKUP_RESTORE_PROCESS.md`.

## 12) Welche Subprocessor werden eingesetzt?
Die aktuelle v1-Liste inklusive Zweck und Datenfluss ist in `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md` dokumentiert. Einige Integrationen sind optional und nur aktiv, wenn entsprechende Umgebungsvariablen gesetzt sind.

## 13) Wird SSO unterstuetzt?
SSO ist in der Enterprise-Roadmap enthalten, aber nicht als abgeschlossen markiert. Der aktuelle Fokus liegt auf RBAC-MVP und Audit-/Governance-Grundlagen.

## 14) Gibt es ein Vulnerability-Meldeverfahren?
Das Verfahren ist in der Enterprise-Checkliste als offener Foundation-Punkt vorgesehen. Bis zur Finalisierung sollte eine dedizierte Security-Intake-Adresse und Triage-SLA vertraglich benannt werden.

## 15) Welche rechtlichen Unterlagen sind verfuegbar?
Fuer Procurement v1 liegen ein AVV/DPA-Outline, ein SLA-Draft und diese Security-FAQ vor. Finalisierung erfolgt nach Legal-Review und kundenspezifischer Vertragsabstimmung.
