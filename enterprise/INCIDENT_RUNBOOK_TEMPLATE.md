# Incident Runbook Template (v1)

Stand: 2026-05-02
Owner: Engineering + Security
Status: Template

## 1. Zweck und Scope
- Dieses Runbook beschreibt Detection, Bewertung, Eskalation und Kommunikation fuer Security- und Availability-Incidents.
- Scope: Produktionssysteme, Kundendaten, Auth/Zugriff, API- und Dashboard-Verfuegbarkeit.

## 2. Rollen im Incident
- Incident Commander (IC): fuehrt Lage und Entscheidungen
- Tech Lead: technische Analyse und Mitigation
- Communications Lead: interne/externe Kommunikation
- Scribe: Timeline und Entscheidungen dokumentieren

## 3. Severity Matrix
- Sev 1 (kritisch):
  - Breiter Ausfall oder potenzieller Datenabfluss
  - Initiale Kundenkommunikation: <= 60 Minuten
- Sev 2 (hoch):
  - Starke Einschraenkung zentraler Funktionen
  - Initiale Kundenkommunikation: <= 4 Stunden
- Sev 3 (mittel):
  - Teilfunktion betroffen, Workaround verfuegbar
  - Kommunikation: im regulaeren Updatezyklus
- Sev 4 (niedrig):
  - Geringe Auswirkung, kein unmittelbares Kundenrisiko

## 4. Trigger und Eingangskanaele
- Monitoring-Alert
- Interne Meldung (Team)
- Kundenmeldung (Support)
- Security Intake Mail (z. B. security@...)

## 5. Triage-Checkliste (erste 15 Minuten)
- Incident-ID erstellen:
- Zeitpunkt der Entdeckung:
- Betroffene Systeme/Endpoints:
- Potenziell betroffene Kunden/Tenants:
- Datentypen betroffen (ja/nein):
- Vorlaeufige Severity:
- IC benannt (Name):

## 6. Eskalationspfad
- Sev 1: IC + CTO/Head of Eng + Security + Support sofort
- Sev 2: IC + Eng Lead + Support innerhalb 30 Minuten
- Sev 3/4: Ticket + zustaendiges Team im naechsten Bereitschaftsfenster

## 7. Technische Reaktion
- Eindammen:
  - Zugriffe begrenzen, Tokens/API-Keys rotieren, Features ggf. deaktivieren
- Ursacheanalyse:
  - Logs, Audit Events, Deploy-Historie, Infrastruktur-Aenderungen
- Wiederherstellung:
  - Fix ausrollen, Services validieren, Monitoring pruefen

## 8. Kommunikationsvorlagen
### 8.1 Interne Erstmeldung
Betreff: [INCIDENT][SEV-X] <Kurzbeschreibung>  
Inhalt:
- Was passiert ist
- Betroffene Systeme
- Vorlaeufige Auswirkung
- Naechstes Update um <Uhrzeit>

### 8.2 Kunden-Erstmeldung
Betreff: Incident Notice [SEV-X] - <Service/Feature>  
Inhalt:
- Wir untersuchen aktuell eine Stoerung von <Service>.
- Startzeit (UTC): <Zeit>
- Aktueller Impact: <Beschreibung>
- Naechstes Update: <Zeit>

### 8.3 Abschlussmeldung
Betreff: Resolved Incident [SEV-X] - <Service/Feature>  
Inhalt:
- Incident beendet um <Zeit>
- Root Cause (kurz)
- Korrekturmassnahmen
- Praeventive Follow-ups

## 9. Abschlusskriterien
- Service stabil und Monitoring gruen
- Kommunikationsabschluss gesendet
- Timeline und Entscheidungen dokumentiert
- Follow-up Tickets erstellt und priorisiert

## 10. Postmortem Template (innerhalb 5 Arbeitstage)
- Incident-ID:
- Zeitraum:
- Impact (Kunden, Daten, Verfuegbarkeit):
- Root Cause:
- Was gut lief:
- Was verbessert werden muss:
- Konkrete Massnahmen mit Owner + Due Date:

## 11. KPI fuer Incident-Prozess
- MTTD (Mean Time to Detect)
- MTTR (Mean Time to Resolve)
- Zeit bis Erstkommunikation
- Anteil wiederkehrender Ursachen
