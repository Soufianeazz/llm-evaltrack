# AVV/DPA Template v1 (Finalizable)

Stand: 2026-05-02
Status: Template ready for legal redline

## Präambel
Diese Vereinbarung zur Auftragsverarbeitung ("AVV"/"DPA") regelt die Verarbeitung personenbezogener Daten durch den Auftragsverarbeiter im Auftrag des Verantwortlichen gemäß anwendbarem Datenschutzrecht.

## 1. Parteien
- Verantwortlicher:
  - Name:
  - Anschrift:
  - Kontakt:
- Auftragsverarbeiter:
  - Name: AgentLens
  - Anschrift:
  - Kontakt:

## 2. Gegenstand und Dauer
- Gegenstand: Bereitstellung und Betrieb der AgentLens Observability Platform.
- Dauer: Laufzeit des Hauptvertrags zzgl. vertraglich definierter Nachlauf- und Löschfristen.

## 3. Art und Zweck der Verarbeitung
- Erhebung, Speicherung, Auswertung, Export und Löschung von Telemetrie- und Betriebsdaten.
- Zweck: Bereitstellung von Monitoring-, Qualitäts- und Compliance-Funktionen.

## 4. Kategorien personenbezogener Daten und betroffener Personen
- Datenkategorien:
  - Prompt-, Input- und Output-Inhalte
  - Metadaten (Modell, Token, Kosten, Zeitstempel)
  - Account-/Nutzerdaten (z. B. E-Mail, Rollen)
  - Audit- und Betriebsdaten
- Betroffene Personen:
  - Mitarbeitende des Verantwortlichen
  - Endnutzer des Verantwortlichen (soweit in Inhalten enthalten)

## 5. Weisungsrecht
- Verarbeitung erfolgt ausschließlich nach dokumentierter Weisung des Verantwortlichen.
- Weisungen sind in Textform zu erteilen (z. B. E-Mail, Ticket, Vertragsanhang).

## 6. Technische und organisatorische Maßnahmen (TOMs)
- Zugriffskontrolle:
  - API-Key-Authentifizierung
  - Admin-restringierte Endpunkte
  - RBAC-Mindestmodell (Admin, Analyst, Read-only) im Ausbau
- Vertraulichkeit:
  - TLS in Transit
  - Verschlüsselung ruhender Backup-Daten
- Integrität:
  - Audit-Logs für Compliance- und Key-Management-Aktionen
- Verfügbarkeit:
  - Health-Endpunkte und internes Alerting
  - Backup-/Restore-Prozess mit Restore-Drills
- Trennung:
  - API-key-isolierter Datenzugriff pro Projektkontext

## 7. Unterauftragsverarbeiter
- Es gilt die veröffentlichte Subprocessor-Liste unter:
  - `/subprocessors`
- Änderungen werden gemäß vertraglicher Regelung angekündigt.

## 8. Drittlandtransfer
- Drittlandtransfers erfolgen nur auf geeigneter Rechtsgrundlage (z. B. SCCs), sofern anwendbar.

## 9. Unterstützungspflichten
- Unterstützung bei Betroffenenrechten (Auskunft, Löschung, Berichtigung, Portabilität) im vertraglich vereinbarten Rahmen.

## 10. Meldung von Datenschutzvorfällen
- Der Auftragsverarbeiter informiert den Verantwortlichen ohne unangemessene Verzögerung nach Bekanntwerden eines bestätigten Vorfalls.
- Erstmeldung enthält mindestens:
  - Art des Vorfalls
  - betroffene Datenkategorien
  - bekannte Auswirkungen
  - eingeleitete Gegenmaßnahmen

## 11. Löschung und Rückgabe
- Nach Vertragsende werden Daten gemäß vereinbarten Fristen gelöscht oder zurückgegeben.
- Exportfunktionen stehen gemäß Plattformfunktionen zur Verfügung.

## 12. Nachweise und Auditrechte
- Auf Anfrage werden geeignete Sicherheits- und Compliance-Nachweise bereitgestellt.
- Audits erfolgen nach angemessener Vorankündigung und unter Wahrung von Vertraulichkeit.

## 13. Haftung und Schlussbestimmungen
- Im Übrigen gelten die Haftungs- und Vertragsbedingungen des Hauptvertrags.

## Anlagen (empfohlen)
- Anlage 1: TOMs (detailliert)
- Anlage 2: Subprocessor-Liste
- Anlage 3: Sicherheits- und Incident-Prozessreferenzen
