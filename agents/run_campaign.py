"""
Orchestrator — führt Lead Finder + Outreach Agent hintereinander aus.

Verwendung:
    python agents/run_campaign.py                  # Alles: suchen + senden
    python agents/run_campaign.py --dry-run        # Suchen + generieren, NICHT senden
    python agents/run_campaign.py --outreach-only  # Nur Outreach (leads.csv muss existieren)

Benötigte Umgebungsvariablen:
    ANTHROPIC_API_KEY   — für E-Mail-Generierung (Pflicht)
    GMAIL_USER          — deine Gmail-Adresse (optional, ohne = nur Preview)
    GMAIL_APP_PASSWORD  — Google App-Passwort  (optional)
    GITHUB_TOKEN        — erhöht GitHub Rate Limit (optional, empfohlen)
"""
import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.lead_finder import find_leads
from agents.outreach_agent import run_outreach


async def main():
    parser = argparse.ArgumentParser(description="AgentLens Marketing Automation")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Leads suchen und E-Mails generieren, aber NICHT versenden"
    )
    parser.add_argument(
        "--outreach-only", action="store_true",
        help="Lead-Suche überspringen (nutzt bestehende leads.csv)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  AgentLens — Marketing Automation")
    print("=" * 55 + "\n")

    # ── Step 1: Leads finden ──────────────────────────────────
    if not args.outreach_only:
        print("SCHRITT 1: GitHub nach Leads durchsuchen...\n")
        leads = await find_leads()
        print(f">> {len(leads)} Leads gefunden\n")
    else:
        print("SCHRITT 1: übersprungen (--outreach-only)\n")

    # ── Step 2: Outreach ──────────────────────────────────────
    print("SCHRITT 2: Outreach E-Mails generieren & senden...\n")
    await run_outreach(dry_run=args.dry_run)

    print("\nFertig! Nächste Schritte:")
    print("  1. agents/outreach_preview.txt öffnen — alle generierten E-Mails prüfen")
    print("  2. agents/leads.csv öffnen — Status 'sent' / 'draft' prüfen")
    print("  3. AgentLens Dashboard: https://llm-evaltrack-production.up.railway.app/traces.html")
    print()


if __name__ == "__main__":
    asyncio.run(main())
