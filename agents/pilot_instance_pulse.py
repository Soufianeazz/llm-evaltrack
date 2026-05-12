"""
Pilot instance pulse — Tier-1 monitoring agent for active pilot deployments.

Twice a day: triggers /admin/pilot-pulse on agentlens.one. The endpoint pings
every registered pilot instance's opt-in healthcheck URL and updates
last_pinged_at. We then evaluate the report and email Soufian when a pilot
instance has been unreachable for more than 6 hours — that's a signal the
pilot customer (the pilot customer) might be stuck or the container died unattended.

NOT pinging customer URLs from this agent directly — Railway → customer URL
is more likely to succeed than GH-runner → customer URL (loopback / RFC1918
URLs are common). Server-side pinging keeps things consistent.

Required env: AGENTLENS_URL, ADMIN_TOKEN, plus the standard SendGrid trio.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request

logger = logging.getLogger("pilot-instance-pulse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

URL = os.environ.get("AGENTLENS_URL", "https://www.agentlens.one").rstrip("/")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
STALE_HOURS = float(os.environ.get("PILOT_STALE_HOURS", "6"))


def trigger_pulse() -> dict | None:
    req = urllib.request.Request(
        f"{URL}/admin/pilot-pulse",
        method="POST",
        headers={
            "X-Admin-Token": ADMIN_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "agentlens-pilot-pulse/1.0",
        },
        data=b"{}",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("HTTP %s: %s", e.code, e.read()[:300])
        return None
    except Exception:
        logger.exception("Pulse request failed")
        return None


def send_email(subject: str, body: str) -> None:
    api_key = os.environ.get("SENDGRID_API_KEY")
    sender = os.environ.get("SENDER_EMAIL")
    recipient = os.environ.get("OPS_EMAIL")
    if not (api_key and sender and recipient):
        logger.info("Email creds missing — would have sent: %s", subject)
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        msg = Mail(from_email=sender, to_emails=recipient, subject=subject, plain_text_content=body)
        SendGridAPIClient(api_key).send(msg)
    except Exception:
        logger.exception("SendGrid send failed: %s", subject)


def main() -> int:
    if not ADMIN_TOKEN:
        logger.error("ADMIN_TOKEN missing — refusing")
        return 1

    payload = trigger_pulse()
    if payload is None:
        return 1

    checked = payload.get("checked", 0)
    results = payload.get("results", []) or []

    if checked == 0:
        logger.info("No pilot instances with healthcheck URLs — nothing to do.")
        return 0

    healthy = [r for r in results if r.get("ok")]
    failing = [r for r in results if not r.get("ok")]

    logger.info(
        "Pilot pulse: checked=%s healthy=%s failing=%s",
        checked, len(healthy), len(failing),
    )

    if not failing:
        return 0

    # Render report
    lines = []
    for r in failing:
        bits = [f"  ✗ {r.get('label', '?')} — status={r.get('status')}"]
        if r.get("error"):
            bits.append(f"    error: {r['error']}")
        bits.append(f"    url: {r.get('url')}")
        lines.append("\n".join(bits))

    body = (
        f"Pilot instance pulse — {len(failing)}/{checked} unreachable.\n\n"
        + "\n\n".join(lines)
        + "\n\nIf this persists for >2 cycles (>{stale} h), reach out to the customer directly.\n"
        f"Last run: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(payload.get('timestamp', time.time())))}\n"
    ).format(stale=STALE_HOURS)

    send_email(
        f"[Pilot] ⚠️ {len(failing)} pilot instance(s) unreachable",
        body,
    )
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    raise SystemExit(main())
