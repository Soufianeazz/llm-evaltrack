"""
PyPI stats — daily Tier-1 read-only agent.

Augments the existing weekly-pypi-report.yml (which keeps a GitHub-Issue thread)
with a DAILY pulse that detects week-over-week drops early. Emails Soufian only
on meaningful regressions or growth spikes — not every day.

Logic:
  1. Fetch current stats from pypistats.org (no auth needed, public).
  2. Compare last_week against the value 7 days ago via local cache file.
  3. Email on:
       - drop >= 30% WoW   → "[PyPI] ⚠️ downloads down X%"
       - growth >= 100% WoW → "[PyPI] 📈 downloads up X% — share-worthy"
  4. Always store today's snapshot for tomorrow's comparison.

Cache lives in repo at `agents/pypi_stats_history.json` and is committed back
by the workflow (same pattern as `agents/leads.csv`).

Required env: SENDGRID_API_KEY, SENDER_EMAIL, OPS_EMAIL.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

logger = logging.getLogger("pypi_stats")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = REPO_ROOT / "agents" / "pypi_stats_history.json"

PACKAGE = os.environ.get("PYPI_PACKAGE", "agentlens-monitor")
DROP_THRESHOLD = float(os.environ.get("PYPI_DROP_THRESHOLD", "0.30"))   # 30%
SPIKE_THRESHOLD = float(os.environ.get("PYPI_SPIKE_THRESHOLD", "1.00"))  # 100%
HISTORY_DAYS = int(os.environ.get("PYPI_HISTORY_DAYS", "30"))


def fetch_stats() -> dict:
    url = f"https://pypistats.org/api/packages/{PACKAGE}/recent"
    req = Request(url, headers={"User-Agent": "agentlens-pypi-stats/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("data", {}) or {}
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return {}


def load_history() -> list[dict]:
    if not CACHE_FILE.exists():
        return []
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Cache file unreadable — starting fresh")
        return []


def save_history(history: list[dict]) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    # Trim to most recent HISTORY_DAYS entries (sorted ascending by date).
    history.sort(key=lambda x: x.get("date", ""))
    if len(history) > HISTORY_DAYS:
        history = history[-HISTORY_DAYS:]
    CACHE_FILE.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def find_entry(history: list[dict], n_days_ago: int) -> dict | None:
    target = datetime.now(timezone.utc).date()
    target_str = (target.toordinal() - n_days_ago)
    # Pick the closest entry within ±2 days of n_days_ago to be tolerant of missed runs.
    best = None
    best_dist = 99
    for h in history:
        try:
            d = datetime.fromisoformat(h["date"]).date().toordinal()
        except Exception:
            continue
        dist = abs((target.toordinal() - d) - n_days_ago)
        if dist < best_dist:
            best_dist = dist
            best = h
    return best if best_dist <= 2 else None


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
        logger.info("Sent: %s", subject)
    except Exception:
        logger.exception("Email send failed: %s", subject)


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    today = datetime.now(timezone.utc).date().isoformat()
    stats = fetch_stats()
    last_week = stats.get("last_week")
    last_day = stats.get("last_day")
    last_month = stats.get("last_month")

    if last_week is None:
        logger.warning("pypistats returned no last_week — abort silently")
        return 0

    logger.info(
        "PyPI stats: last_day=%s last_week=%s last_month=%s",
        last_day, last_week, last_month,
    )

    history = load_history()
    seven_days_ago = find_entry(history, 7)
    today_entry = {
        "date": today,
        "last_day": last_day,
        "last_week": last_week,
        "last_month": last_month,
    }

    # Avoid duplicating today if rerun
    history = [h for h in history if h.get("date") != today]
    history.append(today_entry)
    save_history(history)

    # Compute WoW
    if seven_days_ago and seven_days_ago.get("last_week"):
        prev = seven_days_ago["last_week"]
        if prev > 0:
            change = (last_week - prev) / prev
            logger.info("WoW change: prev=%s curr=%s change=%.1f%%", prev, last_week, change * 100)
            if change <= -DROP_THRESHOLD:
                send_email(
                    f"[PyPI] ⚠️ downloads down {abs(change)*100:.0f}% WoW",
                    (
                        f"agentlens-monitor weekly downloads dropped {abs(change)*100:.0f}%.\n\n"
                        f"  This week: {last_week}\n"
                        f"  Last week: {prev}\n"
                        f"  Diff:      {last_week - prev}\n\n"
                        "Possible causes: marketing campaign ended, search ranking drop, "
                        "or a published bug. Check Google Search Console + recent commits.\n\n"
                        f"Source: https://pypistats.org/packages/{PACKAGE}\n"
                    ),
                )
            elif change >= SPIKE_THRESHOLD:
                send_email(
                    f"[PyPI] 📈 downloads up {change*100:.0f}% WoW",
                    (
                        f"agentlens-monitor weekly downloads spiked {change*100:.0f}%.\n\n"
                        f"  This week: {last_week}\n"
                        f"  Last week: {prev}\n\n"
                        "Worth investigating which channel drove this — could be share-worthy on social "
                        "or a sign that a specific blog post is converting.\n\n"
                        f"Source: https://pypistats.org/packages/{PACKAGE}\n"
                    ),
                )
        else:
            logger.info("Previous week was 0 — skip WoW comparison")
    else:
        logger.info("No history 7 days ago — collecting baseline")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
