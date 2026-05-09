"""
Backup runner — Tier-2 narrow-scope auto-remediation.

Weekly: pulls a SQLite snapshot of agentlens.one's production DB via
POST /admin/backup/snapshot. The snapshot is returned by the SQLite Backup API
(safe under concurrent writes). The CI workflow then attaches it as a GitHub
Actions artifact (90-day retention) — off-Railway disaster recovery.

Blast radius:
  - Read-only on source DB (uses sqlite3.Connection.backup(), not file copy).
  - Output never leaves the GitHub Actions runner unless explicitly downloaded.
  - Encrypted in transit (HTTPS to agentlens.one).

Required env: AGENTLENS_URL, ADMIN_TOKEN.
Output: writes binary to BACKUP_OUTPUT (default: ./backup.db) + prints metadata to stdout.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import urllib.error
import urllib.request

logger = logging.getLogger("backup-runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

URL = os.environ.get("AGENTLENS_URL", "https://www.agentlens.one").rstrip("/")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
OUTPUT = os.environ.get("BACKUP_OUTPUT", "backup.db")
TIMEOUT = float(os.environ.get("BACKUP_TIMEOUT", "180"))


def main() -> int:
    if not ADMIN_TOKEN:
        logger.error("ADMIN_TOKEN missing — refusing to run")
        return 1

    target = f"{URL}/admin/backup/snapshot"
    logger.info("Fetching snapshot from %s", target)

    req = urllib.request.Request(
        target,
        method="POST",
        headers={
            "X-Admin-Token": ADMIN_TOKEN,
            "User-Agent": "agentlens-backup-runner/1.0",
            "Content-Type": "application/json",
        },
        data=b"{}",
    )

    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            disposition = resp.headers.get("Content-Disposition", "")
            with open(OUTPUT, "wb") as f:
                bytes_written = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_written += len(chunk)
    except urllib.error.HTTPError as e:
        logger.error("HTTP %s: %s", e.code, e.read()[:300])
        return 1
    except Exception:
        logger.exception("Backup fetch failed")
        return 1

    elapsed = time.time() - started

    # Sanity check: must be a valid SQLite file
    with open(OUTPUT, "rb") as f:
        header = f.read(16)
    if not header.startswith(b"SQLite format 3"):
        logger.error("Downloaded file is NOT a SQLite database (header=%r)", header)
        return 1

    logger.info(
        "Backup complete: %s bytes in %.1fs → %s",
        bytes_written, elapsed, OUTPUT,
    )
    logger.info("Content-Type: %s", content_type)
    logger.info("Content-Disposition: %s", disposition)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    raise SystemExit(main())
