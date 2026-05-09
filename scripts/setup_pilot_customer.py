"""
End-to-end pilot setup helper.

What it does:
1) Creates a pilot API key via /admin/api-keys
2) Builds a ready-to-share access package
3) Runs pilot smoke test (optional)
4) Runs guardian once (optional)
5) Writes a markdown package to enterprise/

Usage:
  python scripts/setup_pilot_customer.py --customer "Bibin Prathap" --contact-email "bibin@example.com"

Required env vars:
  ADMIN_TOKEN

Optional env vars:
  AGENTLENS_BASE_URL (default: https://www.agentlens.one)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


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


def _request(method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        status = resp.getcode()
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {"raw": raw[:500]}
    return status, body


def _create_pilot_key(base_url: str, admin_token: str, label: str, plan: str, role: str) -> str:
    status, body = _request(
        "POST",
        f"{base_url}/admin/api-keys",
        {
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
        {
            "label": label,
            "plan": plan,
            "role": role,
        },
    )
    if status != 200:
        raise RuntimeError(f"create key failed: status={status} body={body}")
    key = body.get("key")
    if not key:
        raise RuntimeError(f"missing key in response: {body}")
    return key


def _find_existing_key(base_url: str, admin_token: str, label: str) -> str | None:
    status, body = _request(
        "GET",
        f"{base_url}/admin/api-keys",
        {
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
        None,
    )
    if status != 200 or not isinstance(body, list):
        return None
    for item in body:
        if item.get("label") == label and item.get("active", True):
            return item.get("key")
    return None


def _smoke(base_url: str, api_key: str) -> dict:
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    try:
        ingest_status, ingest_body = _request(
            "POST",
            f"{base_url}/ingest",
            headers,
            {
                "input": f"pilot setup smoke input {datetime.now(timezone.utc).isoformat()}",
                "output": "pilot setup smoke output",
                "prompt": "pilot setup check",
                "model": "gpt-4o-mini",
                "metadata": {"feature": "pilot_setup_smoke", "cost_usd": 0.0002},
            },
        )
        trace_status, trace_body = _request(
            "POST",
            f"{base_url}/traces",
            headers,
            {"name": f"pilot_setup_{uuid.uuid4().hex[:10]}"},
        )
        trace_id = trace_body.get("trace_id") or trace_body.get("id")
        if not trace_id:
            raise RuntimeError(f"missing trace id: {trace_body}")
        span_status, span_body = _request(
            "POST",
            f"{base_url}/traces/{trace_id}/spans",
            headers,
            {"name": "setup_span", "span_type": "custom"},
        )
        span_id = span_body.get("span_id") or span_body.get("id")
        if not span_id:
            raise RuntimeError(f"missing span id: {span_body}")
        end_span_status, _ = _request(
            "POST",
            f"{base_url}/traces/{trace_id}/spans/{span_id}/end",
            headers,
            {"status": "completed", "cost_usd": 0.0001},
        )
        end_trace_status, _ = _request(
            "POST",
            f"{base_url}/traces/{trace_id}/end",
            headers,
            {"status": "completed"},
        )
        get_trace_status, get_trace_body = _request("GET", f"{base_url}/traces/{trace_id}", headers, None)
        ok = (
            ingest_status == 202
            and trace_status == 200
            and span_status == 200
            and end_span_status == 200
            and end_trace_status == 200
            and get_trace_status == 200
            and (get_trace_body.get("trace_id") == trace_id or get_trace_body.get("id") == trace_id)
        )
        return {
            "ok": ok,
            "ingest_status": ingest_status,
            "request_id": ingest_body.get("request_id"),
            "create_trace_status": trace_status,
            "create_span_status": span_status,
            "end_span_status": end_span_status,
            "end_trace_status": end_trace_status,
            "get_trace_status": get_trace_status,
            "trace_id": trace_id,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _guardian_once(base_url: str, api_key: str, customer: str) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.pilot_guardian import run_once

    return run_once(base_url=base_url, api_key=api_key, customer=customer, include_e2e=True)


def _build_package(base_url: str, customer: str, contact_email: str, key: str, label: str, smoke: dict, guardian: dict) -> str:
    dashboard = f"{base_url}/dashboard?api_key={key}"
    traces = f"{base_url}/traces.html?api_key={key}"
    debug = f"{base_url}/debug.html?api_key={key}"
    compliance = f"{base_url}/compliance.html?api_key={key}"
    ingest = f"{base_url}/ingest"
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    return f"""# Pilot Access Package: {customer}

Generated: {now_utc}
Contact: {contact_email or "n/a"}
Label: {label}

## Access
- API key: `{key}`
- Ingest URL: {ingest}
- Dashboard: {dashboard}
- Traces: {traces}
- Prompt Debugger: {debug}
- Compliance: {compliance}

## Validation
- Smoke ok: {smoke.get("ok")}
- Guardian ok: {guardian.get("ok")}
- Smoke request_id: {smoke.get("request_id", "n/a")}
- Guardian failed_count: {guardian.get("failed_count", "n/a")}

## SDK snippet
```python
import agentlens
agentlens.init(api_url="{ingest}", api_key="{key}")
agentlens.patch_openai()
agentlens.patch_anthropic()
```

## Background monitor
```bash
export AGENTLENS_BASE_URL="{base_url}"
export PILOT_ALERT_WEBHOOK_URL="<optional_webhook>"
python scripts/pilot_guardian.py --api-key "{key}" --customer "{customer}" --interval-sec 300
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup a pilot customer package end-to-end.")
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--contact-email", default="", help="Customer contact email")
    parser.add_argument("--plan", default="pilot")
    parser.add_argument("--role", default="admin", choices=["admin", "analyst", "read_only"])
    parser.add_argument("--label-prefix", default="pilot")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-guardian-once", action="store_true")
    parser.add_argument("--redact-output", action="store_true", help="Mask API key in stdout; full key is still written to the access package.")
    args = parser.parse_args()

    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if not admin_token:
        raise SystemExit("ADMIN_TOKEN missing")
    base_url = os.getenv("AGENTLENS_BASE_URL", "https://www.agentlens.one").rstrip("/")

    slug = _slugify(args.customer)
    date_text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    label = f"{args.label_prefix}:{slug}:{date_text}"

    try:
        key = _find_existing_key(base_url=base_url, admin_token=admin_token, label=label)
        created = False
        if not key:
            key = _create_pilot_key(
                base_url=base_url,
                admin_token=admin_token,
                label=label,
                plan=args.plan,
                role=args.role,
            )
            created = True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"create key failed: HTTP {exc.code} {detail}") from exc
    except Exception as exc:
        raise SystemExit(f"create key failed: {exc}") from exc

    smoke = {"ok": None, "skipped": True}
    if not args.skip_smoke:
        smoke = _smoke(base_url=base_url, api_key=key)

    guardian = {"ok": None, "skipped": True}
    if not args.skip_guardian_once:
        guardian = _guardian_once(base_url=base_url, api_key=key, customer=args.customer)

    package_text = _build_package(
        base_url=base_url,
        customer=args.customer,
        contact_email=args.contact_email,
        key=key,
        label=label,
        smoke=smoke,
        guardian=guardian,
    )

    out_dir = Path("enterprise")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"PILOT_ACCESS_{_slugify(args.customer)}_{date_text}.md"
    out_file.write_text(package_text, encoding="utf-8")

    result = {
        "customer": args.customer,
        "contact_email": args.contact_email,
        "label": label,
        "created_new_key": created,
        "api_key": (f"{key[:6]}...{key[-4:]}" if args.redact_output else key),
        "base_url": base_url,
        "smoke": smoke,
        "guardian_once": guardian,
        "package_file": str(out_file),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
