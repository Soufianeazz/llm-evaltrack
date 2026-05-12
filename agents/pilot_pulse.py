"""
Pilot Pulse — Soufian's autonomous nudge for an active 14-day pilot.

Three modes:
  --mode daily             Daily status email TO SOUFIAN (Day X of 14, hours-to-next-call, suggested today's actions).
  --mode pre-call          Mon/Thu evening: pre-call briefing for tomorrow's Tue/Fri review slot.
  --mode customer-reminder Day 10/13/14/18 reminder TO THE CUSTOMER (soft-landing
                           around the 14-day pilot end + 7-day grace period).
                           No-op on every other day so daily cron is safe.

Reads:   agents/pilot_state.json  (kickoff date, contact, workflow context)
Sends:   email to OPS_EMAIL via SENDGRID_API_KEY (same channel as the marketing campaign)
LLM:     Claude (ANTHROPIC_API_KEY) generates concise talking points; falls back to a
         deterministic template if the API is unavailable, so cron never silently fails.

Required env:
  ANTHROPIC_API_KEY    optional but recommended (smarter briefings)
  SENDGRID_API_KEY     required to actually deliver email
  SENDER_EMAIL         required (verified sender)
  OPS_EMAIL            required (where the briefings go — Soufian's inbox)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("pilot_pulse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "agents" / "pilot_state.json"
EXAMPLE_FILE = REPO_ROOT / "agents" / "pilot_state.example.json"


def _state_from_env() -> dict | None:
    """Build pilot state entirely from PILOT_* env vars (preferred for CI/CD).
    Returns None if no PILOT_CONTACT_EMAIL is set — caller falls back to JSON.
    Customer PII never lives in the repo this way; secrets only in
    GitHub Actions secrets / the runtime environment.
    """
    email = os.environ.get("PILOT_CONTACT_EMAIL", "").strip()
    if not email:
        return None
    return {
        "pilot_name": os.environ.get("PILOT_NAME", "Active Pilot"),
        "contact_name": os.environ.get("PILOT_CONTACT_NAME", "Customer"),
        "contact_email": email,
        "kickoff_date_utc": os.environ.get("PILOT_KICKOFF_DATE_UTC", ""),
        "pilot_days": int(os.environ.get("PILOT_DAYS", "14")),
        "review_slots_cet": [s.strip() for s in os.environ.get("PILOT_REVIEW_SLOTS", "Tue 16:00,Fri 11:00").split(",")],
        "workflows": [w.strip() for w in os.environ.get("PILOT_WORKFLOWS", "primary").split(",")],
        "stack": [s.strip() for s in os.environ.get("PILOT_STACK", "self-hosted").split(",")],
        "success_criteria": [s.strip() for s in os.environ.get("PILOT_SUCCESS_CRITERIA", "evaluation").split("|")],
        "conversion_target_eur_mo": int(os.environ.get("PILOT_CONVERSION_TARGET_EUR_MO", "2999")),
        "log": [],
    }


def _cet_now() -> datetime:
    """CET/CEST naive-aware. Tries IANA tzdata; falls back to a fixed CET offset
    when tzdata isn't present (some Windows installs). Good enough for scheduling
    review-call reminders — DST drift of one hour is acceptable here."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Berlin"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=1)))


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    """Resolution order:
    1. Environment variables (PILOT_CONTACT_EMAIL, etc.) — preferred for CI/CD
       since customer PII never touches the repo.
    2. Local pilot_state.json — gitignored; for local dev / one-off runs.
    3. pilot_state.example.json — placeholder template; allows the script to
       run cleanly in fresh checkouts but emits no real customer mail.
    """
    env_state = _state_from_env()
    if env_state is not None:
        return env_state
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if EXAMPLE_FILE.exists():
        logger.warning("Using pilot_state.example.json — no real pilot configured.")
        return json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))
    raise SystemExit(f"No pilot state found (env vars, {STATE_FILE}, or {EXAMPLE_FILE}).")


def parse_kickoff(state: dict) -> datetime | None:
    raw = state.get("kickoff_date_utc")
    if not raw or "REPLACE" in raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        logger.warning("Invalid kickoff_date_utc: %s", raw)
        return None


def days_into_pilot(kickoff: datetime, total: int) -> tuple[int, int]:
    now_utc = datetime.now(timezone.utc)
    elapsed = (now_utc - kickoff).days
    day_x = max(1, min(total, elapsed + 1))
    days_left = max(0, total - elapsed)
    return day_x, days_left


def hours_to_next_call(now_cet: datetime) -> tuple[str, float]:
    """Next Tue 16:00 or Fri 11:00 CET, whichever is sooner."""
    candidates: list[tuple[str, datetime]] = []
    for offset in range(0, 8):
        d = now_cet + timedelta(days=offset)
        if d.weekday() == 1:  # Tue
            slot = d.replace(hour=16, minute=0, second=0, microsecond=0)
            if slot > now_cet:
                candidates.append(("Tue 16:00 CET", slot))
        if d.weekday() == 4:  # Fri
            slot = d.replace(hour=11, minute=0, second=0, microsecond=0)
            if slot > now_cet:
                candidates.append(("Fri 11:00 CET", slot))
    if not candidates:
        return "—", 0.0
    label, slot = min(candidates, key=lambda x: x[1])
    return label, round((slot - now_cet).total_seconds() / 3600, 1)


# ── Brief generation ──────────────────────────────────────────────────────────

def fallback_daily(state: dict, day_x: int, days_left: int, next_call: str, hours: float) -> str:
    return (
        f"Pilot Status — Day {day_x} of {state['pilot_days']}\n\n"
        f"Pilot:     {state['pilot_name']}\n"
        f"Contact:   {state['contact_name']} <{state['contact_email']}>\n"
        f"Days left: {days_left}\n"
        f"Next call: {next_call} (in {hours} h)\n\n"
        "Suggested today:\n"
        "  • If silent for >24h → ping the pilot customer with a one-liner ('quick check — anything blocking?')\n"
        "  • If first-call complete → confirm trace ingest is green via /healthz screenshot\n"
        "  • Mid-pilot (Day 7) → draft check-in email with his own dashboard numbers\n"
        "  • Day 12+ → start drafting pricing memo for conversion call\n"
    )


def fallback_precall(state: dict, slot: str) -> str:
    return (
        f"Pre-Call Briefing — {slot}\n\n"
        f"Pilot:   {state['pilot_name']}\n"
        f"With:    {state['contact_name']}\n\n"
        "Suggested talking points:\n"
        "  1. What did you trace this week — any traces where root-cause took >5 min?\n"
        "  2. Hallucination/citation flag counts — which workflow scores worse?\n"
        "  3. Any cost-sensitive workloads where you fell back to GPT-4o vs Ollama?\n"
        "  4. Friction with the dashboard — anything missing or confusing?\n"
        "  5. Headcount that touched AgentLens this week (sets seat-pricing baseline)\n\n"
        "Listen for:\n"
        "  • 'It would be nice if X' → feature request, capture verbatim\n"
        "  • 'We had to work around Y' → friction, urgent fix candidate\n"
        "  • 'My team also wants this' → expansion signal\n"
    )


def llm_brief(prompt: str, fallback: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return fallback
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=os.environ.get("PULSE_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=600,
            system="You are a pragmatic pilot-program operator. Output plain text, no markdown headers, max 250 words. Speak directly to the recipient (Soufian).",
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), None)
        return (text or "").strip() or fallback
    except Exception as exc:
        logger.warning("LLM brief failed (%s) — using fallback", exc)
        return fallback


# ── Email delivery ────────────────────────────────────────────────────────────

def send_email(subject: str, body: str) -> None:
    api_key = os.environ.get("SENDGRID_API_KEY")
    sender = os.environ.get("SENDER_EMAIL")
    recipient = os.environ.get("OPS_EMAIL")
    if not (api_key and sender and recipient):
        logger.warning("Email creds incomplete — printing to stdout instead")
        print(f"\n=== {subject} ===\n{body}\n")
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        message = Mail(
            from_email=sender,
            to_emails=recipient,
            subject=subject,
            plain_text_content=body,
        )
        resp = SendGridAPIClient(api_key).send(message)
        logger.info("Sent: %s (status=%s)", subject, resp.status_code)
    except Exception:
        logger.exception("Email send failed — body below for manual recovery")
        print(f"\n=== {subject} ===\n{body}\n")


# ── Modes ─────────────────────────────────────────────────────────────────────

def run_daily(state: dict) -> None:
    kickoff = parse_kickoff(state)
    now_cet = _cet_now()

    if kickoff is None:
        # Kickoff hasn't happened yet — nudge Soufian about the upcoming call.
        next_call, hours = hours_to_next_call(now_cet)
        body = (
            f"Pilot Status — Pre-Kickoff\n\n"
            f"Pilot:     {state['pilot_name']}\n"
            f"Contact:   {state['contact_name']} <{state['contact_email']}>\n"
            f"Status:    kickoff_date_utc not set in pilot_state.json\n"
            f"Next slot: {next_call} (in {hours} h)\n\n"
            "Action: after the kickoff call, set kickoff_date_utc in agents/pilot_state.json so the "
            "Day-X countdown starts running."
        )
        send_email(f"[Pilot Pulse] Pre-kickoff — next slot in {hours} h", body)
        return

    day_x, days_left = days_into_pilot(kickoff, state["pilot_days"])
    next_call, hours = hours_to_next_call(now_cet)

    fallback = fallback_daily(state, day_x, days_left, next_call, hours)
    prompt = (
        f"Pilot context: {state['pilot_name']} for {state['contact_name']}. "
        f"Today is Day {day_x} of {state['pilot_days']} ({days_left} days left). "
        f"Next review call: {next_call} in {hours} hours. "
        f"Workflows: {', '.join(state['workflows'])}. "
        f"Success criteria: {', '.join(state['success_criteria'])}.\n\n"
        "Write a 200-word pulse email to Soufian: 1) state Day X clearly, 2) suggest 2-3 concrete "
        "actions FOR TODAY based on where we are in the pilot timeline (different at Day 1 vs Day 7 "
        "vs Day 13), 3) one risk to watch for at this stage. End with the next-call line."
    )
    body = llm_brief(prompt, fallback)
    send_email(f"[Pilot Pulse] Day {day_x}/{state['pilot_days']} — next call in {hours}h", body)


CUSTOMER_REMINDER_TEMPLATES = {
    10: (
        "Pilot Day 10 — quick heads-up",
        "Hi {first_name},\n\n"
        "Quick heads-up: we're at Day 10 of the 14-day {pilot_label} pilot. The "
        "Day-14 review call (Tue/Fri slot, whichever lands first) is the natural "
        "moment to decide on conversion to the Scale plan.\n\n"
        "If it would help to align on pricing, contract, or anything procurement-side "
        "before then, just reply and we'll set up a separate slot.\n\n"
        "Also happy to keep it as is and discuss on the regular review call.\n\n"
        "Best,\nSoufian\nhttps://www.agentlens.one\n",
    ),
    13: (
        "Pilot Day 13 — tomorrow's call is the decision point",
        "Hi {first_name},\n\n"
        "Tomorrow's call wraps the 14-day {pilot_label} pilot. To make it easy:\n\n"
        "  - If you want to convert to Scale (€2,999/mo): I'll send the contract "
        "    after the call and we'll keep your existing instance running uninterrupted.\n"
        "  - If you need more evaluation time: we have a 7-day grace window built in. "
        "    Your API key keeps working until Day 21 so you can finish any in-flight "
        "    workflows or share findings internally.\n"
        "  - If it's not the right fit: just say so on the call and we'll part on "
        "    good terms — I'll send you a 1-page write-up of what we measured.\n\n"
        "All three are valid outcomes. See you tomorrow.\n\n"
        "Best,\nSoufian\n",
    ),
    14: (
        "Pilot Day 14 — final-day reminder",
        "Hi {first_name},\n\n"
        "Today's review call is the official end of the 14-day {pilot_label} pilot. "
        "Whatever we decide on the call, here's what happens technically:\n\n"
        "  - Convert to Scale: your existing API key is upgraded server-side, no "
        "    container restart needed.\n"
        "  - Keep evaluating: 7-day grace begins, key valid through Day 21.\n"
        "  - Wind down: I'll send a final summary with extraction instructions for "
        "    your trace data — your SQLite volume is yours, no lock-in.\n\n"
        "Talk in a few hours.\n\n"
        "Best,\nSoufian\n",
    ),
    18: (
        "Pilot grace period — 3 days left",
        "Hi {first_name},\n\n"
        "Quick reminder: you're 4 days into the 7-day grace period after the "
        "{pilot_label} pilot. Your API key remains valid through Day 21 (3 days from "
        "today).\n\n"
        "If the conversion call hasn't happened yet or you need more time, no problem — "
        "just reply and we'll find another slot. After Day 21 the key stops accepting "
        "new ingest, but your existing trace data remains on your container's local "
        "SQLite volume and is fully exportable via the compliance endpoint.\n\n"
        "Best,\nSoufian\n",
    ),
}


def first_name(full: str) -> str:
    return (full or "").split()[0] if full else "there"


def run_customer_reminder(state: dict) -> None:
    """Send the customer (not Soufian) a soft-landing email on milestone days.
    No-op on every other day so daily cron is safe to run unconditionally."""
    kickoff = parse_kickoff(state)
    if kickoff is None:
        logger.info("Kickoff date not set — customer reminders skipped.")
        return

    # Uncapped day count — customer-reminder needs to fire on grace-period days
    # (15-21) which days_into_pilot() caps at pilot_days (14).
    elapsed_days = (datetime.now(timezone.utc) - kickoff).days
    day_x = max(1, elapsed_days + 1)
    template = CUSTOMER_REMINDER_TEMPLATES.get(day_x)
    if not template:
        logger.info("Day %s — no customer reminder scheduled, skipping.", day_x)
        return

    contact_email = state.get("contact_email", "")
    if not contact_email or "REPLACE" in contact_email:
        logger.warning("contact_email not set in pilot_state.json — cannot send Day %s reminder.", day_x)
        return

    subject_tmpl, body_tmpl = template
    fmt = {
        "first_name": first_name(state.get("contact_name", "")),
        "pilot_label": state.get("pilot_name", "AgentLens").split(" ")[0],
    }
    subject = subject_tmpl.format(**fmt)
    body = body_tmpl.format(**fmt)

    api_key = os.environ.get("SENDGRID_API_KEY")
    sender = os.environ.get("SENDER_EMAIL")
    if not (api_key and sender):
        logger.warning("Email creds incomplete — printing customer reminder for manual send")
        print(f"\n=== TO: {contact_email} | {subject} ===\n{body}\n")
        return

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        cc = os.environ.get("OPS_EMAIL")  # cc Soufian so he sees what went out
        message = Mail(
            from_email=sender,
            to_emails=contact_email,
            subject=subject,
            plain_text_content=body,
        )
        if cc:
            message.add_cc(cc)
        resp = SendGridAPIClient(api_key).send(message)
        logger.info("Sent Day-%s reminder to %s (status=%s)", day_x, contact_email, resp.status_code)
    except Exception:
        logger.exception("Customer reminder send failed — body below for manual recovery")
        print(f"\n=== TO: {contact_email} | {subject} ===\n{body}\n")


def run_precall(state: dict) -> None:
    now_cet = _cet_now()
    next_call, hours = hours_to_next_call(now_cet)
    if hours > 24 or hours < 1:
        logger.info("Next call is %s h away — outside pre-call window, skipping.", hours)
        return

    fallback = fallback_precall(state, next_call)
    kickoff = parse_kickoff(state)
    day_x_str = "pre-kickoff"
    if kickoff:
        day_x, _ = days_into_pilot(kickoff, state["pilot_days"])
        day_x_str = f"Day {day_x} of {state['pilot_days']}"

    prompt = (
        f"Tomorrow Soufian has a {next_call} review call with {state['contact_name']} "
        f"about the {state['pilot_name']} (currently {day_x_str}). "
        f"Workflows: {', '.join(state['workflows'])}. "
        f"Success criteria: {', '.join(state['success_criteria'])}.\n\n"
        "Write a pre-call briefing in plain text, max 250 words: "
        "1) one-line context recap, "
        "2) FIVE specific questions Soufian should ask (numbered), tailored to where we are in the pilot, "
        "3) THREE listening signals (expansion, friction, conversion intent). "
        "Be concrete and pilot-specific, not generic."
    )
    body = llm_brief(prompt, fallback)
    send_email(f"[Pilot Pulse] Pre-call brief — {next_call} (in {hours}h)", body)


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "pre-call", "customer-reminder"], required=True)
    args = parser.parse_args()

    state = load_state()
    if args.mode == "daily":
        run_daily(state)
    elif args.mode == "pre-call":
        run_precall(state)
    else:
        run_customer_reminder(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
