"""
Agent 2 — Outreach Agent
Liest Leads aus leads.csv, schreibt personalisierte E-Mails mit Claude
und versendet sie automatisch via Gmail.

Verwendung:
    python agents/outreach_agent.py --dry-run   # Nur generieren, nicht senden
    python agents/outreach_agent.py             # Generieren + Senden
"""
import csv
import os
import sys
import asyncio
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic

try:
    import agentlens
    from agentlens import trace_agent
    TRACING = True
except ImportError:
    TRACING = False

# ── Konfiguration ──────────────────────────────────────────────
AGENTLENS_URL     = os.getenv("AGENTLENS_URL", "https://llm-evaltrack-production.up.railway.app")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_USER        = os.getenv("GMAIL_USER", "")          # deine@gmail.com
GMAIL_APP_PW      = os.getenv("GMAIL_APP_PASSWORD", "")  # Google App-Passwort (nicht dein normales PW)

SENDER_NAME   = "Soufian Azzaoui"
PRODUCT_NAME  = "AgentLens"
PRODUCT_URL   = "https://llm-evaltrack-production.up.railway.app/landing.html"
LEADS_FILE    = Path(__file__).parent / "leads.csv"
PREVIEW_FILE  = Path(__file__).parent / "outreach_preview.txt"
MAX_LEADS     = 15   # Maximale Leads pro Run
# ───────────────────────────────────────────────────────────────


def generate_email(client: Anthropic, lead: dict) -> dict:
    """Claude schreibt eine personalisierte E-Mail für den Lead."""
    prompt = f"""Du schreibst eine Cold-Outreach-E-Mail für AgentLens — ein LLM-Observability-Tool.
AgentLens ist wie LangSmith, aber selbst-gehostet, DSGVO-konform und günstiger (€199/Monat).
Es tracked LLM-Kosten, Antwortqualität und Agent-Traces in einem Dashboard.

Lead-Infos:
- Name: {lead['name']}
- GitHub: {lead['github_user']}
- Repo: {lead['repo_name']} — {lead['repo_description']}
- Stars: {lead['repo_stars']}
- Bio: {lead['bio']}
- Firma: {lead['company']}

Schreibe eine kurze, persönliche Cold-E-Mail (max. 100 Wörter). Regeln:
- Beziehe dich natürlich auf ihr konkretes Repo
- Nenne EINEN konkreten Vorteil (z.B. Kosten tracken, Agent-Debugging, DSGVO)
- Keine Buzzwords, kein Verkäufer-Sprech — klingt wie Entwickler zu Entwickler
- Sanfter CTA: kostenlos ausprobieren, kein Kreditkarte nötig
- Auf Englisch (GitHub-Entwickler international)

Format (exakt so):
SUBJECT: <Betreffzeile>
BODY:
<E-Mail-Text>
"""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    subject = ""
    body_lines = []
    in_body = False

    for line in text.split("\n"):
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.strip() == "BODY:":
            in_body = True
        elif in_body:
            body_lines.append(line)

    # Signatur anhängen
    body = "\n".join(body_lines).strip()
    body += f"\n\n--\n{SENDER_NAME}\nAgentLens — LLM Observability\n{PRODUCT_URL}"

    tokens_in  = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost       = tokens_in * 0.00000025 + tokens_out * 0.00000125

    return {"subject": subject, "body": body, "tokens": tokens_in + tokens_out, "cost_usd": cost}


def send_email(to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Sendet E-Mail via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_APP_PW:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{SENDER_NAME} <{GMAIL_USER}>"
    msg["To"]      = f"{to_name} <{to_email}>"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP Fehler: {e}]")
        return False


def load_leads() -> list:
    if not LEADS_FILE.exists():
        print(f"[Fehler] {LEADS_FILE} nicht gefunden. Erst lead_finder.py ausführen.")
        sys.exit(1)
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def save_leads(leads: list):
    with open(LEADS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)


async def run_outreach(dry_run: bool = False):
    if TRACING:
        agentlens.init(api_url=f"{AGENTLENS_URL}/ingest")

    if not ANTHROPIC_API_KEY:
        print("[Fehler] ANTHROPIC_API_KEY nicht gesetzt.")
        sys.exit(1)

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    all_leads = load_leads()

    # Nur Leads mit Email und Status "new"
    actionable = [
        l for l in all_leads
        if l.get("email") and l.get("outreach_status", "new") == "new"
    ][:MAX_LEADS]

    print("=" * 55)
    print(f"  AgentLens — Outreach Agent {'(DRY RUN)' if dry_run else ''}")
    print("=" * 55)
    print(f"  Leads gesamt:     {len(all_leads)}")
    print(f"  Actionable:       {len(actionable)} (Email + neu)")
    print(f"  SMTP konfiguriert: {'Ja' if GMAIL_USER and GMAIL_APP_PW else 'Nein — nur Preview'}")
    print()

    sent_count   = 0
    total_cost   = 0.0
    preview_text = ""

    def _process():
        nonlocal sent_count, total_cost, preview_text

        for lead in actionable:
            print(f"Bearbeite: {lead['name']} ({lead['github_user']})...")

            # E-Mail generieren
            result = generate_email(client, lead)
            total_cost += result["cost_usd"]
            print(f"  Betreff: {result['subject']}")

            # Preview aufbauen
            preview_text += (
                f"{'=' * 50}\n"
                f"TO:      {lead['name']} <{lead['email']}>\n"
                f"SUBJECT: {result['subject']}\n\n"
                f"{result['body']}\n\n"
            )

            # Senden
            email_sent = False
            if not dry_run and lead["email"]:
                email_sent = send_email(
                    to_email=lead["email"],
                    to_name=lead["name"],
                    subject=result["subject"],
                    body=result["body"],
                )

            status = "sent" if email_sent else ("draft" if dry_run else "no_smtp")
            print(f"  Status: {status}")
            if email_sent:
                sent_count += 1

            # Lead in-place updaten
            lead["outreach_status"] = status
            lead["email_subject"]   = result["subject"]
            lead["email_body"]      = result["body"]

    if TRACING:
        with trace_agent("outreach_agent", input=f"{len(actionable)} leads, dry_run={dry_run}") as trace:
            with trace.span("generate_and_send", span_type="llm") as s:
                _process()
                s.set_output(f"{sent_count} gesendet, ${total_cost:.4f}")
                s.set_cost(total_cost)
            trace.set_output(f"{sent_count}/{len(actionable)} E-Mails gesendet")
    else:
        _process()

    # CSV + Preview speichern
    save_leads(all_leads)
    PREVIEW_FILE.write_text(preview_text, encoding="utf-8")

    print(f"\n{'=' * 55}")
    print(f"  E-Mails generiert: {len(actionable)}")
    print(f"  E-Mails gesendet:  {sent_count}")
    print(f"  Kosten (Claude):   ${total_cost:.4f}")
    print(f"  Preview:           {PREVIEW_FILE}")
    if TRACING:
        print(f"  Dashboard:         {AGENTLENS_URL}/traces.html")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentLens Outreach Agent")
    parser.add_argument("--dry-run", action="store_true", help="Nur generieren, nicht senden")
    args = parser.parse_args()
    asyncio.run(run_outreach(dry_run=args.dry_run))
