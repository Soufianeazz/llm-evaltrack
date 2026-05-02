# AVV/DPA Outline (Draft v0.1)

Stand: 2026-05-02
Owner: Legal + Security
Status: Draft

## 1. Parteien und Rollen
- Verantwortlicher (Customer): Name, Anschrift, Kontakt
- Auftragsverarbeiter (AgentLens): Name, Anschrift, Kontakt
- Datenschutzkontakt/DPO: Mailbox und Eskalationskontakt

## 2. Gegenstand und Dauer der Verarbeitung
- Gegenstand: Bereitstellung von AgentLens Observability Platform
- Art der Verarbeitung: Erhebung, Speicherung, Auswertung, Export, Loeschung
- Laufzeit: Vertragslaufzeit + definierte Nachlauf-/Loeschfristen

## 3. Art der Daten und Kategorien betroffener Personen
- Datenkategorien:
  - Prompt-/Response-Inhalte
  - Metadaten (Model, Tokens, Cost, Timestamp)
  - Account-/Nutzerdaten (Name, E-Mail, Rolle)
  - Betriebsdaten (Logs, Audit Events)
- Betroffenengruppen:
  - Mitarbeitende des Kunden
  - Endnutzer des Kunden (falls durch Inhalte betroffen)

## 4. Zweckbindung und dokumentierte Weisungen
- Verarbeitung ausschliesslich zur Vertragserfuellung
- Weisungen nur in Textform (Ticket, E-Mail, Vertragsanhang)
- Umgang mit unklaren/risikoreichen Weisungen

## 5. Technische und Organisatorische Massnahmen (TOMs)
- Zugriffsschutz:
  - Rollenbasiertes Berechtigungskonzept (Admin, Analyst, Read-only)
  - Starke Authentifizierung fuer Admin-Zugaenge
- Vertraulichkeit:
  - TLS fuer Daten in Transit
  - Verschluesselung ruhender Daten (DB/Backups)
- Integritaet:
  - Audit-Logs fuer Admin- und Compliance-Aktionen
  - Change- und Release-Prozess mit Rollback
- Verfuegbarkeit:
  - Monitoring/Alerting
  - Backup-/Restore-Prozess mit Regeltest
- Belastbarkeit:
  - Incident-Runbook und Eskalationspfad
- Trennung:
  - Tenant-/Projekttrennung auf Daten- und API-Ebene

## 6. Unterauftragsverarbeiter (Subprocessor)
- Referenz auf aktuelle Subprocessor-Liste (URL)
- Verfahren fuer neue Subprocessor inkl. Vorankuendigung
- Einspruchsprozess des Kunden

## 7. Drittlandtransfers
- Angaben zu Datenregionen
- Transfermechanismen (falls anwendbar): SCCs, Angemessenheitsbeschluss
- Zusicherungen zu Zugriff und Schutzmassnahmen

## 8. Betroffenenrechte und Supportpflichten
- Unterstuetzung bei Auskunft, Loeschung, Berichtigung, Portabilitaet
- Fristen und SLA fuer Rueckmeldungen

## 9. Meldung von Datenschutzvorfaellen
- Meldeweg und Kontaktpunkt
- Erstinformation innerhalb definierter Frist
- Mindestinhalt einer Vorfallmeldung

## 10. Speicherort, Aufbewahrung, Loeschfristen
- Primaere Speicherregion(en)
- Backup-Aufbewahrung
- Loeschfristen nach Vertragsende
- Nachweisfaehige Loeschung (Protokoll/Audit Event)

## 11. Kontrollrechte und Nachweise
- Bereitstellung von Security-Dokumentation (FAQ, Policies, Pen-Test Summary)
- Audit-Rechte nach Vorankuendigung
- Vertraulichkeitsgrenzen fuer Audit-Unterlagen

## 12. Rueckgabe und Loeschung bei Vertragsende
- Exportmoeglichkeiten (CSV/JSON)
- Zeitfenster fuer Export vor Loeschung
- Endgueltige Loeschbestaetigung

## 13. Haftung, Vertraulichkeit, Schlussbestimmungen
- Verweis auf Hauptvertrag/SLA
- Vertraulichkeitsklauseln
- Rangfolge bei Widerspruechen zwischen Anlagen

## Offene Punkte fuer Finalisierung
- Juristische Endredaktion nach Zielmarkt (DE/EU/US)
- Exakte Fristen fuer Retention und Incident-Kommunikation
- Finale Subprocessor-URL und Change-Notification-Prozess
