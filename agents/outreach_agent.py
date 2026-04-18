"""
Agent 2 — Outreach Agent
Liest Leads aus leads.csv, schreibt personalisierte E-Mails mit Claude
und versendet sie automatisch via SendGrid.

Verwendung:
    python agents/outreach_agent.py --dry-run   # Nur generieren, nicht senden
    python agents/outreach_agent.py             # Generieren + Senden
"""
import csv
import os
import sys
import asyncio
import argparse
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

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
SENDGRID_API_KEY  = os.getenv("SENDGRID_API_KEY", "")    # SendGrid API Key (SG.xxx...)
SENDER_EMAIL      = os.getenv("SENDER_EMAIL", "soufian.azzaoui@icloud.com")  # verifizierte Absender-Email

SENDER_NAME      = "Soufian Azzaoui"
PRODUCT_NAME     = "AgentLens"
PRODUCT_URL      = "https://llm-evaltrack-production.up.railway.app/landing.html"
CASE_STUDY_URL   = "https://llm-evaltrack-production.up.railway.app/case_study.html"
LEADS_FILE       = Path(__file__).parent / "leads.csv"
PREVIEW_FILE     = Path(__file__).parent / "outreach_preview.txt"
MAX_LEADS        = 15   # Maximale Leads pro Run
# ───────────────────────────────────────────────────────────────


def generate_email(client: Anthropic, lead: dict) -> dict:
    """Claude schreibt eine personalisierte E-Mail für den Lead."""
    prompt = f"""You are writing a cold outreach email for AgentLens — a self-hosted LLM observability tool.

AgentLens key facts:
- Self-hosted (data never leaves your infra) — unlike LangSmith or Helicone
- Auto quality scoring + hallucination detection on every LLM call (zero config)
- Agent waterfall debugger: see which step failed, how long, what it cost
- GDPR-native: built for EU teams with compliance requirements
- 2-line integration: patch_openai() or patch_anthropic()
- Case study: a German legal tech team cut debugging time by 90% and prevented €1,200 in wasted API costs

Lead info:
- Name: {lead['name']}
- GitHub: {lead['github_user']}
- Repo: {lead['repo_name']} — {lead['repo_description']}
- Stars: {lead['repo_stars']}
- Bio: {lead['bio']}
- Company: {lead['company']}

Write a short, personal cold email (max 90 words). Rules:
- Reference their specific repo or work naturally in the first sentence
- Pick ONE pain point relevant to their project (cost control, agent debugging, or GDPR/data privacy)
- Link to the case study as proof: {CASE_STUDY_URL}
- CTA: ask for a 20-minute demo, not "try for free"
- Tone: developer-to-developer, no buzzwords, no sales speak
- Write in English

Format (exactly):
SUBJECT: <subject line>
BODY:
<email body>
"""

    response = client.messages.create(
        model="claude-haiku-4-5",
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

    # Platzhalter bereinigen die Claude manchmal lässt
    body = "\n".join(body_lines).strip()
    body = body.replace("[Name]", SENDER_NAME)
    body = body.replace("[Your Name]", SENDER_NAME)
    body = body.replace("[Your name]", SENDER_NAME)
    body = body.replace("[your name]", SENDER_NAME)
    body = body.replace("[link]", PRODUCT_URL)
    body = body.replace("[Link]", PRODUCT_URL)

    # Signatur anhängen (nur falls noch keine drin)
    if "--" not in body[-80:]:
        body += f"\n\n--\n{SENDER_NAME}\nAgentLens — LLM Observability for EU AI Teams\n{PRODUCT_URL}\nCase study: {CASE_STUDY_URL}"

    tokens_in  = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost       = tokens_in * 0.00000025 + tokens_out * 0.00000125

    return {"subject": subject, "body": body, "tokens": tokens_in + tokens_out, "cost_usd": cost}


def send_email(to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Sendet E-Mail via SendGrid API."""
    if not SENDGRID_API_KEY:
        print("  [SendGrid API Key fehlt — E-Mail nicht gesendet]")
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(SENDER_EMAIL, SENDER_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
            plain_text_content=Content("text/plain", body),
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code in (200, 202)
    except Exception as e:
        print(f"  [SendGrid Fehler: {e}]")
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

    # Safety: nur Leads mit Email + Status in Whitelist ("new" oder "failed" für Retry)
    # Blockiert: sent, draft, replied, bounced, unsubscribed — niemals doppelt kontaktieren
    CONTACTABLE_STATUSES = {"new", "failed", ""}
    skipped_already_contacted = sum(
        1 for l in all_leads
        if l.get("email") and l.get("outreach_status", "new") not in CONTACTABLE_STATUSES
    )
    actionable = [
        l for l in all_leads
        if l.get("email") and l.get("outreach_status", "new") in CONTACTABLE_STATUSES
    ][:MAX_LEADS]

    print("=" * 55)
    print(f"  AgentLens — Outreach Agent {'(DRY RUN)' if dry_run else ''}")
    print("=" * 55)
    print(f"  Leads gesamt:       {len(all_leads)}")
    print(f"  Bereits kontaktiert:{skipped_already_contacted} (übersprungen)")
    print(f"  Actionable:         {len(actionable)} (Email + neu/failed)")
    print(f"  SendGrid:           {'Ja' if SENDGRID_API_KEY else 'Nein (nur Preview)'}")
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
