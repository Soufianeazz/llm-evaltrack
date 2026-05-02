# Security FAQ Struktur (v0.1)

Stand: 2026-05-02
Owner: Security + Solutions Engineering
Zielgruppe: IT, InfoSec, Procurement
Status: Struktur freigegeben, Antworten ausstehend

## 0. Dokumentsteuerung
- Version, Datum, Owner
- Gueltigkeitsbereich (Produkt, Cloud/Self-host)
- Kontakt fuer Security-Fragen

## 1. Unternehmen und Governance
- Wer ist AgentLens? (Entity, Sitz, Kontakt)
- Gibt es ein Security-Programm und Verantwortlichkeiten?
- Wie werden Security-Risiken bewertet und priorisiert?

## 2. Produktarchitektur und Datenfluss
- Welche Komponenten verarbeiten Kundendaten?
- Wie erfolgt Tenant-/Projekttrennung?
- Welche Daten verlassen die Kundenumgebung (wenn ueberhaupt)?

## 3. Datenklassifikation und PII
- Welche Datentypen werden verarbeitet?
- Wie wird PII erkannt oder minimiert?
- Welche Konfigurationen gibt es fuer Maskierung/Redaktion?

## 4. Zugriffskontrolle und Authentifizierung
- Welche Rollen gibt es (Admin, Analyst, Read-only)?
- Wie werden Nutzer angelegt/deaktiviert?
- Ist MFA/SSO verfuegbar oder geplant?

## 5. Verschluesselung und Schluesselmanagement
- Verschluesselung in Transit (TLS-Versionen, Zertifikate)
- Verschluesselung at Rest (Datenbank, Backups)
- Wer verwaltet Schluessel und Rotation?

## 6. Logging, Audit und Monitoring
- Welche sicherheitsrelevanten Events werden geloggt?
- Wie lange werden Audit-Logs aufbewahrt?
- Gibt es Alerts fuer Anomalien/Ausfaelle?

## 7. Vulnerability Management
- Wie koennen Schwachstellen gemeldet werden?
- Welche Triage- und Fix-SLAs gelten?
- Gibt es regelmaessige Scans/Reviews?

## 8. Incident Response
- Wie wird ein Security Incident klassifiziert?
- Wie schnell werden Kunden informiert?
- Welche Informationen werden in Incident-Updates geliefert?

## 9. Business Continuity, Backup und Recovery
- Wie sehen Backup-Frequenz und Aufbewahrung aus?
- Wann wurde der letzte Restore-Test durchgefuehrt?
- Gibt es ein dokumentiertes Disaster-Recovery-Verfahren?

## 10. Subprocessor und Drittlandtransfer
- Welche Subprocessor werden eingesetzt und warum?
- In welchen Regionen werden Daten verarbeitet?
- Welche Transfermechanismen werden genutzt?

## 11. Compliance und Vertragsunterlagen
- Ist ein DPA/AVV verfuegbar?
- Welche Annexe/Policies werden bereitgestellt?
- Welche Supportzeiten und SLA-Optionen gibt es?

## 12. Kundenkontrollen und Datenrechte
- Wie funktionieren Export, Loeschung und Retention?
- Wie werden DSAR-Anfragen unterstuetzt?
- Welche Admin-Kontrollen hat der Kunde selbst?

## 13. Secure Development Lifecycle (optional, empfohlen)
- Code Reviews, Teststrategie, Release-Freigaben
- Secret Management und Zugriff auf Produktionssysteme
- Abhaengigkeitsmanagement und Patch-Prozess

## Antwortformat pro Frage
- Kurzantwort (2-4 Saetze)
- Technischer Nachweis/Beleg (Policy, Screenshot, API-Endpoint)
- Verweis auf weiterfuehrendes Dokument

## Minimalpaket fuer v1
- 20-30 Top-Fragen aus Sections 2, 4, 5, 6, 7, 8, 10, 11
- Einheitliches Antwortniveau (nicht marketinglastig)
- Abnahme durch Security + Legal + Sales
