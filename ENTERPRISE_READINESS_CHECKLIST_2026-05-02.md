# AgentLens Enterprise Readiness Checklist
Start: **2026-05-02**  
Ziel: Abschlussfähigkeit für Enterprise-Deals in 90 Tagen.

## Erfolgskriterien (Definition of Done)
- Security- und Compliance-Paket verkaufsfähig (DPA/AVV, SLA, Security FAQ, Subprocessor-Liste).
- Enterprise-Trust-Funktionen live (SSO/RBAC/Audit-Exports/Retention-Policies klar dokumentiert).
- Operative Zuverlässigkeit nachweisbar (Monitoring, Incident-Runbook, Backup/Restore-Test).
- Sales-Enablement fertig (1-pager, Security one-pager, Live-POC-Playbook, Referenzmaterial).

## Priorität (Reihenfolge)
1. Vertrags- und Security-Basics
2. Zugriffs- und Governance-Funktionen
3. Reliability + Ops-Nachweise
4. Sales- und Procurement-Unterlagen

---

## Phase 1 (Tag 1–30) – Foundation

### Security & Compliance
- [x] Finales DPA/AVV Template erstellen (inkl. TOMs, Speicherort, Löschfristen). (2026-05-02, siehe `enterprise/AVV_DPA_TEMPLATE_V1_FINAL.md`)
- [x] Subprocessor-Liste veröffentlichen (inkl. Zweck, Region, Link). (2026-05-02, siehe `dashboard/subprocessors.html` + `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`)
- [x] Security-Policy-Seite live: Auth, Verschlüsselung, Logging, Backups. (2026-05-02, siehe `dashboard/security.html`)
- [x] Vulnerability-Prozess definieren (Intake-Mail, Triage-SLA, Disclosure-Text). (2026-05-02, siehe `enterprise/VULNERABILITY_DISCLOSURE_PROCESS.md`)

### Produkt (Must-have für Enterprise-Piloten)
- [x] RBAC-Minimum live: `Admin`, `Analyst`, `Read-only`. (2026-05-02, siehe `enterprise/RBAC_IMPLEMENTATION_STATUS_2026-05-02.md` + Rollen-Enforcement in API)
- [x] API-Key-Rotation-Policy + Audit-Log-Einträge für Rotationen. (2026-05-02, siehe `enterprise/API_KEY_ROTATION_PROCESS_AND_AUDIT_EVENTS.md` + `api/routes/admin.py`)
- [x] Tenant/Projekt-Trennung dokumentieren und im UI klar kennzeichnen. (2026-05-02, siehe `enterprise/TENANT_PROJECT_SEPARATION.md` + Scope-Hinweise in Dashboard-Seiten)
- [x] PII-Handling dokumentieren (Maskierung/Retention/Export/Delete-Flows). (2026-05-02, siehe `enterprise/PII_HANDLING_POLICY.md`)

### Reliability & Ops
- [x] Uptime/Health-Endpunkte + internes Alerting für Ausfälle. (2026-05-02, siehe `/healthz`, `/readyz`, `/health` + `.github/workflows/uptime-health-alert.yml`)
- [x] Backup-Strategie schriftlich: Frequenz, Aufbewahrung, Restore-Schritte. (2026-05-02, siehe `enterprise/BACKUP_RESTORE_PROCESS.md`)
- [x] Einmaliger Restore-Test mit Zeitmessung und Protokoll. (2026-05-02, siehe `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`)
- [x] Incident-Runbook v1 (Severity, Eskalation, Kommunikationsvorlage). (2026-05-02, siehe `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`)

### Sales Enablement
- [x] Security one-pager (2 Seiten) für IT/InfoSec. (2026-05-02, siehe `enterprise/SECURITY_ONE_PAGER_V1.md`)
- [x] Procurement pack v1: DPA, SLA draft, Security FAQ. (2026-05-02, siehe `enterprise/PROCUREMENT_PACK_V1.md`)
- [x] Enterprise-Demo-Skript (20–30 Min) mit Compliance- und Audit-Fokus. (2026-05-02, siehe `enterprise/ENTERPRISE_DEMO_SCRIPT_COMPLIANCE_TRUST_20_30_MIN.md`)

---

## Phase 2 (Tag 31–60) – Hardening

### Security
- [ ] Externer Pentest (oder gleichwertiger Security-Review) beauftragen. (In Vorbereitung seit 2026-05-03; erste Vendor-Antwort eingegangen am 2026-05-04, Follow-up fuer Q3 geplant; siehe `enterprise/PENTEST_VENDOR_SHORTLIST_2026-05-03.md` + `enterprise/PENTEST_VENDOR_OUTREACH_EMAILS_2026-05-03.md`)
- [ ] Findings abarbeiten und Report-Summary freigeben.
- [x] Secret-Management-Härtung (Rotation-Intervalle + Owner). (2026-05-03, siehe `enterprise/SECRET_MANAGEMENT_STANDARD_V1.md` + `enterprise/SECRET_INVENTORY_AND_ROTATION_MATRIX_2026-05-03.md`)

### Produkt
- [x] SSO-Plan entscheiden: SAML oder OIDC (mind. einer produktiv). (2026-05-02, OIDC-first, siehe `enterprise/SSO_DECISION_PLAN_OIDC_FIRST.md`)
- [x] Audit-Log-Export verbessern (CSV/JSON, Filter, Zeiträume). (2026-05-02, siehe `/compliance/audit-log` Filter + `/compliance/audit-log/export`)
- [x] Data retention controls im UI mit klarer Warnlogik. (2026-05-02, siehe Warnlogik in `dashboard/compliance.html`)
- [x] Admin-Aktionen vollständig auditieren (wer/was/wann). (2026-05-02, erweitert in `api/routes/admin.py`, `api/routes/alerts.py`, `api/routes/traces.py`, `api/routes/compliance.py`)

### Reliability
- [x] SLO-Entwurf (z. B. 99.9%) + Error-Budget-Tracking. (2026-05-02, siehe `enterprise/SLO_ERROR_BUDGET_DRAFT.md`)
- [x] Lasttest-Szenario definieren und 1 Benchmark-Lauf protokollieren. (2026-05-02, siehe `enterprise/LOAD_TEST_SCENARIO_AND_BENCHMARK_2026-05-02.md`)
- [x] On-call-Minimum etablieren (wer reagiert wann, Kommunikationspfad). (2026-05-02, siehe `enterprise/ON_CALL_MINIMUM_PLAN.md`)

### Sales
- [x] 2 POC-Designs standardisieren (EU-Compliance Fokus / Cost+Quality Fokus). (2026-05-02, siehe `enterprise/POC_DESIGNS_V1.md`)
- [x] ROI-Rechner für Pilot → Jahresvertrag. (2026-05-02, siehe `enterprise/ROI_CALCULATOR_PILOT_TO_ANNUAL.md`)
- [x] Objection-Handling-Dokument (LangSmith/Langfuse/Datadog-Vergleich). (2026-05-02, siehe `enterprise/OBJECTION_HANDLING_LANGSMITH_LANGFUSE_DATADOG.md`)

---

## Phase 3 (Tag 61–90) – Enterprise Close Readiness

### Compliance & Legal
- [x] SLA finalisieren (Supportzeiten, Reaktionszeiten, Verfügbarkeit). (2026-05-02, siehe `enterprise/SLA_V2_FINAL.md` + `dashboard/sla.html`)
- [x] Security Annex + Data Processing Annex final paketieren. (2026-05-02, siehe `enterprise/SECURITY_ANNEX_V1_FINAL.md` + `enterprise/DATA_PROCESSING_ANNEX_V1_FINAL.md` + `dashboard/legal-pack.html`)
- [x] Standard-Antwortpaket für Security Questionnaires vorbereiten. (2026-05-02, siehe `enterprise/SECURITY_QUESTIONNAIRE_RESPONSE_PACK_V1.md` + `enterprise/SECURITY_QUESTIONNAIRE_TOP30_V2.md` + `dashboard/security-questionnaire.html` + `dashboard/security-questionnaire-v2.html`)

### Produkt & Betrieb
- [ ] SSO/RBAC/Audit-Endzustand live und dokumentiert.
- [ ] Disaster-Recovery-Drill durchführen und dokumentieren.
- [ ] Change-Management-Prozess (Release Notes + Rollback Plan) festziehen.

### GTM / Closing
- [ ] 3 belastbare Case Stories mit klaren Kennzahlen (auch anonymisiert).
- [ ] Pilot-to-Contract Playbook final (Meilensteine, Exit-Kriterien, Entscheider-Matrix).
- [ ] Enterprise Pricing + Vertragslaufzeit-Optionen (1/2/3 Jahre) sauber ausformuliert.

---

## Start ab morgen (2026-05-02) – Tagesplan für die erste Woche

### Tag 1
- [x] AVV/DPA-Outline schreiben. (2026-05-02, siehe `enterprise/AVV_DPA_OUTLINE.md`)
- [x] Security FAQ Struktur festlegen. (2026-05-02, siehe `enterprise/SECURITY_FAQ_STRUCTURE.md`)
- [x] Incident-Runbook Template anlegen. (2026-05-02, siehe `enterprise/INCIDENT_RUNBOOK_TEMPLATE.md`)

### Tag 2
- [x] Subprocessor-Liste und Datenflussdiagramm v1 erstellen. (2026-05-02, siehe `enterprise/SUBPROCESSOR_LIST_AND_DATA_FLOW_V1.md`)
- [x] Backup/Restore-Prozess dokumentieren. (2026-05-02, siehe `enterprise/BACKUP_RESTORE_PROCESS.md`)

### Tag 3
- [x] RBAC-MVP Scope fixieren (Rollen + Rechte-Matrix). (2026-05-02, siehe `enterprise/RBAC_MVP_SCOPE.md`)
- [x] API-Key-Rotation-Prozess inkl. Audit-Events festlegen. (2026-05-02, siehe `enterprise/API_KEY_ROTATION_PROCESS_AND_AUDIT_EVENTS.md`)

### Tag 4
- [x] Procurement-Paket v1 zusammenstellen (AVV draft, SLA draft, FAQ). (2026-05-02, siehe `enterprise/PROCUREMENT_PACK_V1.md`)
- [x] Enterprise-Demo-Skript auf Compliance/Trust ausrichten. (2026-05-02, siehe `enterprise/ENTERPRISE_DEMO_SCRIPT_COMPLIANCE_TRUST_20_30_MIN.md`)

### Tag 5
- [x] Restore-Test durchführen und Ergebnis protokollieren. (2026-05-02, siehe `enterprise/RESTORE_TEST_PROTOCOL_2026-05-02.md`)
- [x] Woche-1 Review: Gaps, Blocker, nächste 2 Wochen priorisieren. (2026-05-02, siehe `enterprise/WEEK1_REVIEW_2026-05-02.md`)

### Tag 6
- [x] Security Questionnaire Response Pack v1 erstellen (Standardantworten für Procurement/InfoSec). (2026-05-02, siehe `enterprise/SECURITY_QUESTIONNAIRE_RESPONSE_PACK_V1.md`)
- [x] Öffentliche Questionnaire-Seite unter Clean URL veröffentlichen. (2026-05-02, siehe `/security-questionnaire` + `dashboard/security-questionnaire.html`)

### Tag 7
- [x] SLA v2 finalisieren und customer-shareable dokumentieren. (2026-05-02, siehe `enterprise/SLA_V2_FINAL.md`)
- [x] Öffentliche SLA-Seite unter Clean URL veröffentlichen. (2026-05-02, siehe `/sla` + `dashboard/sla.html`)

### Tag 8
- [x] Security Annex v1 Final und Data Processing Annex v1 Final paketieren. (2026-05-02, siehe `enterprise/SECURITY_ANNEX_V1_FINAL.md` + `enterprise/DATA_PROCESSING_ANNEX_V1_FINAL.md`)
- [x] Öffentliche Legal-Pack-Seite unter Clean URL veröffentlichen. (2026-05-02, siehe `/legal-pack` + `dashboard/legal-pack.html`)

### Tag 9
- [x] Security Questionnaire Top-30 v2 erstellen (Q&A Standardantwortpaket). (2026-05-02, siehe `enterprise/SECURITY_QUESTIONNAIRE_TOP30_V2.md`)
- [x] Öffentliche Questionnaire-v2-Seite unter Clean URL veröffentlichen. (2026-05-02, siehe `/security-questionnaire-v2` + `dashboard/security-questionnaire-v2.html`)

---

## Metriken (wöchentlich tracken)
- [ ] # Enterprise-ready Unterlagen fertig (Soll: +2/Woche)
- [ ] # Security/Compliance Gaps offen (Soll: fallend)
- [ ] Median Response-Zeit auf Lead-Anfragen (Soll: < 24h)
- [ ] # aktive Enterprise-Piloten (Soll: steigend)
- [ ] Pilot→Vertragsquote (Soll: steigende Tendenz)
