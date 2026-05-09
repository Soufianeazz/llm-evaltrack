"""
Demo freshness keeper — Tier-2 narrow-scope auto-remediation.

Calls POST /admin/seed-demo on agentlens.one every day. The endpoint is idempotent
(see api/routes/admin.py:_do_seed_demo) and tops up the demo dataset so that every
visitor lands on a dashboard showing recent activity.

Why this exists:
  - seed_demo_on_startup() only runs when the container restarts.
  - Railway can run the same container for a week+ without a deploy.
  - After 24h with no traffic, the demo dashboard shows "0 calls in 24h" → kills conversion.

This agent's blast radius is narrow on purpose:
  - Only one endpoint called (/admin/seed-demo).
  - Endpoint is idempotent — replays don't accumulate spam data.
  - Cannot delete, cannot mutate user data, cannot change billing.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger("demo-freshness")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

URL = os.environ.get("AGENTLENS_URL", "https://www.agentlens.one").rstrip("/")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def main() -> int:
    if not ADMIN_TOKEN:
        logger.error("ADMIN_TOKEN missing — refusing to proceed")
        return 1

    req = urllib.request.Request(
        f"{URL}/admin/seed-demo",
        method="POST",
        headers={
            "X-Admin-Token": ADMIN_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "agentlens-demo-freshness/1.0",
        },
        data=b"{}",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
            logger.info(
                "Demo refreshed: status=%s requests=%s recent_24h=%s",
                payload.get("status"),
                payload.get("requests_total") or payload.get("requests"),
                payload.get("recent_24h", "?"),
            )
            return 0
    except urllib.error.HTTPError as e:
        logger.error("HTTP %s: %s", e.code, e.read().decode("utf-8", errors="replace")[:300])
        return 1
    except Exception:
        logger.exception("Demo refresh failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
