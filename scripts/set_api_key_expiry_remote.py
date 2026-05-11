"""
Set an API key expiry through the live AgentLens admin API.

Reads ADMIN_TOKEN from the environment and never prints the full API key.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request


def build_payload(days: int, expires_at: float | None) -> dict:
    if expires_at is not None:
        return {"expires_at": expires_at}
    if days <= 0:
        raise ValueError("days must be greater than zero")
    return {"trial_days": days}


def mask_key(key: str) -> str:
    if len(key) < 12:
        return key[:3] + "..."
    return f"{key[:6]}...{key[-4:]}"


def set_remote_expiry(
    base_url: str,
    api_key: str,
    admin_token: str,
    days: int,
    expires_at: float | None,
) -> dict:
    payload = build_payload(days, expires_at)
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/admin/api-keys/{api_key}/expiry",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    body = json.loads(raw)
    body["input_key"] = mask_key(api_key)
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Set live AgentLens API key expiry via admin API.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--expires-at", type=float, default=None)
    parser.add_argument("--base-url", default="https://www.agentlens.one")
    args = parser.parse_args()

    admin_token = os.environ.get("ADMIN_TOKEN", "").strip()
    if not admin_token:
        raise SystemExit("ADMIN_TOKEN missing")
    result = set_remote_expiry(
        base_url=args.base_url,
        api_key=args.api_key,
        admin_token=admin_token,
        days=args.days,
        expires_at=args.expires_at,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
