"""
Pilot demo smoke test for AgentLens hosted API.

What it does:
1) Sends one /ingest event
2) Creates + ends one trace and one span
3) Verifies trace can be fetched

Usage:
    python scripts/pilot_demo_smoke.py --api-key <pilot_key>

Optional env vars:
    AGENTLENS_BASE_URL (default: https://www.agentlens.one)
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import urllib.error
import urllib.request


def _request(method: str, url: str, headers: dict, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.getcode()
        raw = resp.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw[:500]}
    return status, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentLens pilot smoke test.")
    parser.add_argument("--api-key", required=True, help="Pilot API key")
    args = parser.parse_args()

    base_url = os.getenv("AGENTLENS_BASE_URL", "https://www.agentlens.one").rstrip("/")
    headers = {"Content-Type": "application/json", "X-API-Key": args.api_key}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    local_trace_ref = f"pilot-smoke-{uuid.uuid4().hex[:10]}"

    try:
        ingest_payload = {
            "input": f"pilot smoke input {ts}",
            "output": "pilot smoke output",
            "prompt": "Validate pilot path",
            "model": "gpt-4o-mini",
            "metadata": {"feature": "pilot_smoke", "cost_usd": 0.0002},
        }
        ingest_status, ingest_body = _request("POST", f"{base_url}/ingest", headers, ingest_payload)

        create_trace_status, create_trace_body = _request(
            "POST",
            f"{base_url}/traces",
            headers,
            {"name": f"pilot_smoke_trace_{local_trace_ref}"},
        )
        trace_id = create_trace_body.get("trace_id") or create_trace_body.get("id")
        if not trace_id:
            raise RuntimeError(f"Missing trace_id in response: {create_trace_body}")

        create_span_status, span_body = _request(
            "POST",
            f"{base_url}/traces/{trace_id}/spans",
            headers,
            {"name": "pilot_smoke_span", "span_type": "custom"},
        )
        span_id = span_body.get("span_id") or span_body.get("id")
        if not span_id:
            raise RuntimeError(f"Missing span id in response: {span_body}")

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
            {"status": "completed", "output": "pilot smoke done"},
        )

        get_trace_status, get_trace_body = _request(
            "GET",
            f"{base_url}/traces/{trace_id}",
            headers,
            None,
        )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {exc.code}: {detail}")
        return 2
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}")
        return 3

    ok = (
        ingest_status == 202
        and create_trace_status == 200
        and create_span_status == 200
        and end_span_status == 200
        and end_trace_status == 200
        and get_trace_status == 200
        and (get_trace_body.get("trace_id") == trace_id or get_trace_body.get("id") == trace_id)
    )

    print("=== PILOT DEMO SMOKE ===")
    print(f"base_url:             {base_url}")
    print(f"ingest_status:        {ingest_status}")
    print(f"request_id:           {ingest_body.get('request_id')}")
    print(f"create_trace_status:  {create_trace_status}")
    print(f"create_span_status:   {create_span_status}")
    print(f"end_span_status:      {end_span_status}")
    print(f"end_trace_status:     {end_trace_status}")
    print(f"get_trace_status:     {get_trace_status}")
    print(f"trace_id:             {trace_id}")
    print(f"local_trace_ref:      {local_trace_ref}")
    print(f"result:               {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
