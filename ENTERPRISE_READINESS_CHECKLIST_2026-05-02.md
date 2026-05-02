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
- [ ] Finales DPA/AVV Template erstellen (inkl. TOMs, Speicherort, Löschfristen).
- [ ] Subprocessor-Liste veröffentlichen (inkl. Zweck, Region, Link).
- [ ] Security-Policy-Seite live: Auth, Verschlüsselung, Logging, Backups.
- [ ] Vulnerability-Prozess definieren (Intake-Mail, Triage-SLA, Disclosure-Text).

### Produkt (Must-have für Enterprise-Piloten)
- [ ] RBAC-Minimum live: `Admin`, `Analyst`, `Read-only`.
- [ ] API-Key-Rotation-Policy + Audit-Log-Einträge für Rotationen.
- [ ] Tenant/Projekt-Trennung dokumentieren und im UI klar kennzeichnen.
- [ ] PII-Handling dokumentieren (Maskierung/Retention/Export/Delete-Flows).

### Reliability & Ops
- [ ] Uptime/Health-Endpunkte + internes Alerting für Ausfälle.
- [ ] Backup-Strategie schriftlich: Frequenz, Aufbewahrung, Restore-Schritte.
- [ ] Einmaliger Restore-Test mit Zeitmessung und Protokoll.
- [ ] Incident-Runbook v1 (Severity, Eskalation, Kommunikationsvorlage).

### Sales Enablement
- [ ] Security one-pager (2 Seiten) für IT/InfoSec.
- [ ] Procurement pack v1: DPA, SLA draft, Security FAQ.
- [ ] Enterprise-Demo-Skript (20–30 Min) mit Compliance- und Audit-Fokus.

---

## Phase 2 (Tag 31–60) – Hardening

### Security
- [ ] Externer Pentest (oder gleichwertiger Security-Review) beauftragen.
- [ ] Findings abarbeiten und Report-Summary freigeben.
- [ ] Secret-Management-Härtung (Rotation-Intervalle + Owner).

### Produkt
- [ ] SSO-Plan entscheiden: SAML oder OIDC (mind. einer produktiv).
- [ ] Audit-Log-Export verbessern (CSV/JSON, Filter, Zeiträume).
- [ ] Data retention controls im UI mit klarer Warnlogik.
- [ ] Admin-Aktionen vollständig auditieren (wer/was/wann).

### Reliability
- [ ] SLO-Entwurf (z. B. 99.9%) + Error-Budget-Tracking.
- [ ] Lasttest-Szenario definieren und 1 Benchmark-Lauf protokollieren.
- [ ] On-call-Minimum etablieren (wer reagiert wann, Kommunikationspfad).

### Sales
- [ ] 2 POC-Designs standardisieren (EU-Compliance Fokus / Cost+Quality Fokus).
- [ ] ROI-Rechner für Pilot → Jahresvertrag.
- [ ] Objection-Handling-Dokument (LangSmith/Langfuse/Datadog-Vergleich).

---

## Phase 3 (Tag 61–90) – Enterprise Close Readiness

### Compliance & Legal
- [ ] SLA finalisieren (Supportzeiten, Reaktionszeiten, Verfügbarkeit).
- [ ] Security Annex + Data Processing Annex final paketieren.
- [ ] Standard-Antwortpaket für Security Questionnaires vorbereiten.

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
- [ ] Restore-Test durchführen und Ergebnis protokollieren.
- [ ] Woche-1 Review: Gaps, Blocker, nächste 2 Wochen priorisieren.

---

## Metriken (wöchentlich tracken)
- [ ] # Enterprise-ready Unterlagen fertig (Soll: +2/Woche)
- [ ] # Security/Compliance Gaps offen (Soll: fallend)
- [ ] Median Response-Zeit auf Lead-Anfragen (Soll: < 24h)
- [ ] # aktive Enterprise-Piloten (Soll: steigend)
- [ ] Pilot→Vertragsquote (Soll: steigende Tendenz)
