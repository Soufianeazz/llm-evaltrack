"""
Create a dedicated AgentLens pilot API key and print ready-to-share access links.

Usage:
    python scripts/create_pilot_access.py --customer "Acme GmbH"

Required env vars:
    AGENTLENS_BASE_URL   e.g. https://www.agentlens.one
    ADMIN_TOKEN          admin token used by /admin endpoints
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def _slugify(value: str) -> str:
    out = []
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_"}:
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "pilot-customer"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create AgentLens pilot access package.")
    parser.add_argument("--customer", required=True, help="Customer name, e.g. 'Acme GmbH'")
    parser.add_argument("--plan", default="pilot", help="Plan value for API key (default: pilot)")
    parser.add_argument("--role", default="admin", choices=["admin", "analyst", "read_only"], help="API key role")
    parser.add_argument("--label-prefix", default="pilot", help="Label prefix for the API key")
    args = parser.parse_args()

    base_url = os.getenv("AGENTLENS_BASE_URL", "https://www.agentlens.one").rstrip("/")
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if not admin_token:
        print("[error] ADMIN_TOKEN is not set.", file=sys.stderr)
        return 1

    slug = _slugify(args.customer)
    date_text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    label = f"{args.label_prefix}:{slug}:{date_text}"
    create_url = f"{base_url}/admin/api-keys"

    headers = {
        "Content-Type": "application/json",
        "X-Admin-Token": admin_token,
    }
    payload = {"label": label, "plan": args.plan, "role": args.role}

    try:
        result = _post_json(create_url, payload, headers)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {exc.code} creating pilot key: {body}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[error] Failed to create pilot key: {exc}", file=sys.stderr)
        return 3

    api_key = result.get("key")
    if not api_key:
        print(f"[error] Unexpected response: {result}", file=sys.stderr)
        return 4

    dashboard = f"{base_url}/dashboard?api_key={api_key}"
    traces = f"{base_url}/traces.html?api_key={api_key}"
    compliance = f"{base_url}/compliance.html?api_key={api_key}"
    debug = f"{base_url}/debug.html?api_key={api_key}"
    ingest = f"{base_url}/ingest"

    print("=== PILOT ACCESS PACKAGE ===")
    print(f"Customer:      {args.customer}")
    print(f"Label:         {label}")
    print(f"Plan/Role:     {args.plan}/{args.role}")
    print(f"API Key:       {api_key}")
    print(f"Ingest URL:    {ingest}")
    print(f"Dashboard:     {dashboard}")
    print(f"Traces:        {traces}")
    print(f"Prompt Debug:  {debug}")
    print(f"Compliance:    {compliance}")
    print("")
    print("SDK quick start:")
    print("import agentlens")
    print(f'agentlens.init(api_url="{ingest}", api_key="{api_key}")')
    print("agentlens.patch_openai()")
    print("agentlens.patch_anthropic()")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

