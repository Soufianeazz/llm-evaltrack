"""
Pilot Pulse — Soufian's autonomous nudge for the VeritasGraph 14-day pilot.

Two modes:
  --mode daily       Daily status email (Day X of 14, hours-to-next-call, suggested today's actions).
  --mode pre-call    Mon/Thu evening: pre-call briefing for tomorrow's Tue/Fri review slot.

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
    if not STATE_FILE.exists():
        raise SystemExit(f"pilot_state.json not found at {STATE_FILE}")
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


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
        "  • If silent for >24h → ping Bibin with a one-liner ('quick check — anything blocking?')\n"
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
    parser.add_argument("--mode", choices=["daily", "pre-call"], required=True)
    args = parser.parse_args()

    state = load_state()
    if args.mode == "daily":
        run_daily(state)
    else:
        run_precall(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
