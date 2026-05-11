"""
Set an expiry timestamp for an existing AgentLens API key.

This is intended for already-created pilot keys that predate the `expires_at`
field. It never prints the full key.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.database import SessionFactory, init_db
from storage.models import ApiKey


def resolve_expiry(*, now: float, days: int) -> float:
    return now + days * 24 * 60 * 60


def mask_key(key: str) -> str:
    if len(key) < 12:
        return key[:3] + "..."
    return f"{key[:6]}...{key[-4:]}"


async def set_expiry(key: str, days: int) -> dict:
    if days <= 0:
        raise ValueError("days must be greater than zero")

    await init_db()
    async with SessionFactory() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.key == key))
        obj = result.scalar_one_or_none()
        if obj is None:
            raise LookupError("API key not found")

        now = time.time()
        obj.expires_at = resolve_expiry(now=now, days=days)
        await db.commit()
        return {
            "key": mask_key(key),
            "label": obj.label,
            "plan": obj.plan,
            "active": obj.active,
            "expires_at": obj.expires_at,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Set expiry for an existing AgentLens API key.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    result = asyncio.run(set_expiry(key=args.api_key, days=args.days))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
