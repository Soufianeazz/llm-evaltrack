"""
Pilot guardian loop for 14-day runs.

What it does every interval:
1) Checks health/readiness and key API endpoints
2) Optionally runs an ingest + trace E2E smoke
3) Emits structured JSON logs
4) Sends webhook alerts on failures

Usage:
    python scripts/pilot_guardian.py --api-key <pilot_key> --customer "the pilot customer"
    python scripts/pilot_guardian.py --api-key <pilot_key> --customer "the pilot customer" --once

Optional env vars:
    AGENTLENS_BASE_URL=https://www.agentlens.one
    PILOT_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


def _request(method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.getcode()
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {"raw": raw[:500]}
    return status, body


def _timed_get(base_url: str, path: str, headers: dict[str, str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        status, body = _request("GET", f"{base_url}{path}", headers, None)
        return {
            "path": path,
            "status": status,
            "ok": 200 <= status < 300,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "body_keys": list(body.keys())[:10] if isinstance(body, dict) else [],
        }
    except Exception as exc:
        return {
            "path": path,
            "status": None,
            "ok": False,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "error": str(exc),
        }


def _run_e2e(base_url: str, headers: dict[str, str]) -> dict[str, Any]:
    trace_id = None
    span_id = None
    try:
        ingest_status, ingest_body = _request(
            "POST",
            f"{base_url}/ingest",
            headers,
            {
                "input": f"pilot guardian ingest {datetime.now(timezone.utc).isoformat()}",
                "output": "pilot guardian output",
                "prompt": "monitoring",
                "model": "gpt-4o-mini",
                "metadata": {"feature": "pilot_guardian", "cost_usd": 0.0002},
            },
        )
        create_trace_status, create_trace_body = _request(
            "POST",
            f"{base_url}/traces",
            headers,
            {"name": f"pilot_guardian_{uuid.uuid4().hex[:8]}"},
        )
        trace_id = create_trace_body.get("trace_id") or create_trace_body.get("id")
        if not trace_id:
            raise RuntimeError(f"missing trace_id in response: {create_trace_body}")

        create_span_status, create_span_body = _request(
            "POST",
            f"{base_url}/traces/{trace_id}/spans",
            headers,
            {"name": "guardian_span", "span_type": "custom"},
        )
        span_id = create_span_body.get("span_id") or create_span_body.get("id")
        if not span_id:
            raise RuntimeError(f"missing span id in response: {create_span_body}")

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
            {"status": "completed", "output": "guardian done"},
        )
        get_trace_status, get_trace_body = _request("GET", f"{base_url}/traces/{trace_id}", headers, None)

        ok = (
            ingest_status == 202
            and create_trace_status == 200
            and create_span_status == 200
            and end_span_status == 200
            and end_trace_status == 200
            and get_trace_status == 200
            and (get_trace_body.get("trace_id") == trace_id or get_trace_body.get("id") == trace_id)
        )
        return {
            "ok": ok,
            "ingest_status": ingest_status,
            "request_id": ingest_body.get("request_id"),
            "create_trace_status": create_trace_status,
            "create_span_status": create_span_status,
            "end_span_status": end_span_status,
            "end_trace_status": end_trace_status,
            "get_trace_status": get_trace_status,
            "trace_id": trace_id,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "trace_id": trace_id, "span_id": span_id}


def _post_alert(webhook_url: str, payload: dict[str, Any]) -> None:
    if not webhook_url:
        return
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def run_once(base_url: str, api_key: str, customer: str, include_e2e: bool) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    checks = [
        _timed_get(base_url, "/healthz", {"Content-Type": "application/json"}),
        _timed_get(base_url, "/readyz", {"Content-Type": "application/json"}),
        _timed_get(base_url, "/requests/stats", headers),
        _timed_get(base_url, "/debug/requests?limit=5", headers),
        _timed_get(base_url, "/traces?limit=5", headers),
        _timed_get(base_url, "/compliance/audit-log?limit=5", headers),
    ]

    e2e = _run_e2e(base_url, headers) if include_e2e else {"skipped": True}
    failed = [c for c in checks if not c.get("ok")]
    if include_e2e and not e2e.get("ok"):
        failed.append({"path": "e2e", "status": "fail"})

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "customer": customer,
        "base_url": base_url,
        "ok": len(failed) == 0,
        "checks": checks,
        "e2e": e2e,
        "failed_count": len(failed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentLens pilot guardian loop.")
    parser.add_argument("--api-key", required=True, help="Pilot API key")
    parser.add_argument("--customer", required=True, help="Customer name for logs/alerts")
    parser.add_argument("--interval-sec", type=int, default=300, help="Loop interval (default: 300)")
    parser.add_argument("--max-loops", type=int, default=0, help="0 = infinite loop")
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit")
    parser.add_argument("--no-e2e", action="store_true", help="Disable ingest/trace smoke")
    args = parser.parse_args()

    base_url = os.getenv("AGENTLENS_BASE_URL", "https://www.agentlens.one").rstrip("/")
    webhook_url = os.getenv("PILOT_ALERT_WEBHOOK_URL", "").strip()
    include_e2e = not args.no_e2e

    loops_done = 0
    while True:
        report = run_once(base_url=base_url, api_key=args.api_key, customer=args.customer, include_e2e=include_e2e)
        print(json.dumps(report, ensure_ascii=True))

        if not report.get("ok"):
            _post_alert(
                webhook_url,
                {
                    "text": (
                        f":rotating_light: AgentLens pilot alert for {args.customer}\n"
                        f"failed_checks={report.get('failed_count')} base={base_url}\n"
                        f"ts={report.get('ts')}"
                    ),
                    "kind": "pilot_guardian_alert",
                    "report": report,
                },
            )

        loops_done += 1
        if args.once or (args.max_loops > 0 and loops_done >= args.max_loops):
            return 0 if report.get("ok") else 1
        time.sleep(max(30, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
