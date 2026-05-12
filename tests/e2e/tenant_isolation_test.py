"""
Tenant isolation regression test — runs in CI before every image push.

PURPOSE
-------
Cross-tenant data leaks killed real customer trust at companies like Datadog,
Algolia, and Elastic. After the 2026-05-12 pre-Bibin audit found two real
leaks (audit-log + budget alerts), this test ensures EVERY data-returning
endpoint enforces api_key filtering — and prevents anyone from re-introducing
the same bug class via a future refactor.

WHAT IT DOES
------------
1. Creates two independent tenants (A, B) via /admin/api-keys
2. Tenant A ingests requests, creates traces, sets a budget alert, registers
   a self-host instance
3. For every documented data-returning endpoint, asserts:
   - Tenant B sees ZERO of tenant A's data
   - Cross-tenant ID guessing returns 404 (never 200 with the data)
   - Privileged-only endpoints reject tenant B with 401/403
4. Cleans up after itself so re-running is idempotent

WHY THIS TEST EXISTS (read before deleting any case)
----------------------------------------------------
Each `case` in CHECKED_ENDPOINTS corresponds to either:
  a) A real leak we found and fixed (H1=audit-log, H3=budget) — these MUST
     stay covered or the fix can silently regress under refactor.
  b) A surface that is currently isolated but that a future "let me add a
     convenience admin view" PR could break — these are tripwires.

If a test starts failing because someone "intentionally" widened access,
the fix is not to delete the test — it's to either add an admin gate, or
add an explicit api_key filter, or document why this endpoint is global
(and we put it behind admin-token in that case).
"""
from __future__ import annotations

import os
import sys
import time

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = os.environ.get("AGENTLENS_BASE", "http://localhost:8000").rstrip("/")
ADMIN = os.environ["ADMIN_TOKEN"]
TIMEOUT_S = int(os.environ.get("AGENTLENS_HEALTH_TIMEOUT", "60"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def step(msg: str) -> None:
    print(f"  -> {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"  PASS  {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"\n  FAIL  {msg}\n", flush=True)
    sys.exit(1)


def wait_healthy() -> None:
    deadline = time.time() + TIMEOUT_S
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE}/healthz", timeout=2)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_err = exc
        time.sleep(1)
    fail(f"healthz never responded — {last_err}")


def create_key(label: str, plan: str = "scale") -> str:
    r = requests.post(
        f"{BASE}/admin/api-keys",
        headers={"X-Admin-Token": ADMIN, "Content-Type": "application/json"},
        json={"label": label, "plan": plan, "role": "admin"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"create_key({label}) returned HTTP {r.status_code} — {r.text[:200]}")
    return r.json()["key"]


def auth(key: str) -> dict:
    return {"X-API-Key": key}


# ── Setup tenant A's data ─────────────────────────────────────────────────────

def populate_tenant_a(key_a: str) -> dict:
    """Create one of every data type under tenant A. Return references B will
    try to access."""
    headers = {**auth(key_a), "Content-Type": "application/json"}

    # 1 ingest
    r = requests.post(
        f"{BASE}/ingest",
        headers=headers,
        json={
            "input": "tenant-A-secret-input",
            "output": "tenant-A-secret-output",
            "prompt": "tenant-A-secret-prompt",
            "model": "tenant-a-only-model",
            "metadata": {"input_tokens": 5, "output_tokens": 3, "cost_usd": 0.0001, "feature": "isolation-test"},
        },
        timeout=10,
    )
    if r.status_code not in (200, 201, 202):
        fail(f"tenant A ingest failed: HTTP {r.status_code}")

    # 1 trace + 1 span
    r = requests.post(
        f"{BASE}/traces",
        headers=headers,
        json={"name": "tenant-A-secret-trace", "input": "secret"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"tenant A trace create failed: HTTP {r.status_code}")
    trace_id = r.json()["trace_id"]

    r = requests.post(
        f"{BASE}/traces/{trace_id}/spans",
        headers=headers,
        json={"name": "secret_span", "span_type": "llm", "model": "tenant-a-only-model", "input": "x"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"tenant A span create failed: HTTP {r.status_code}")
    span_id = r.json()["span_id"]

    requests.post(
        f"{BASE}/traces/{trace_id}/spans/{span_id}/end",
        headers=headers,
        json={"status": "completed", "output": "secret"},
        timeout=10,
    )
    requests.post(
        f"{BASE}/traces/{trace_id}/end",
        headers=headers,
        json={"status": "completed", "output": "secret"},
        timeout=10,
    )

    # 1 budget alert with a webhook URL that MUST NOT leak
    r = requests.post(
        f"{BASE}/alerts/budget",
        headers=headers,
        json={
            "daily_budget_usd": 100.0,
            "webhook_url": "https://hooks.tenant-a-secret.example/webhook",
            "email": "tenant-a-secret@example.com",
        },
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"tenant A budget set failed: HTTP {r.status_code}")

    # 1 self-host instance registration
    r = requests.post(
        f"{BASE}/portal/instances",
        headers=headers,
        json={"label": "tenant-A-secret-instance", "pilot": False, "notes": "secret"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"tenant A instance register failed: HTTP {r.status_code}")
    instance_id = r.json()["id"]

    # Wait for async eval worker so /requests/stats reflects ingest
    time.sleep(4)

    return {"trace_id": trace_id, "span_id": span_id, "instance_id": instance_id}


# ── Isolation assertions ──────────────────────────────────────────────────────

def assert_no_leak_in_body(body: bytes | str, label: str, expect_status: int = 200) -> None:
    """Tenant B's response must contain NO tenant-A markers."""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    leaks = []
    for marker in (
        "tenant-A-secret-input",
        "tenant-A-secret-output",
        "tenant-A-secret-prompt",
        "tenant-a-only-model",
        "tenant-A-secret-trace",
        "tenant-A-secret-instance",
        "tenant-a-secret@example.com",
        "tenant-a-secret.example",
    ):
        if marker in body:
            leaks.append(marker)
    if leaks:
        fail(f"{label}: tenant-A data leaked into tenant-B response: {leaks}\n"
             f"Body excerpt: {body[:400]}")


def check_endpoint_isolated(label: str, method: str, path: str, key_b: str,
                            expect_codes: set[int] = {200, 401, 403}) -> None:
    """Call endpoint with tenant B's key, verify response status + no A-markers."""
    headers = auth(key_b)
    if method == "GET":
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=10)
    elif method == "DELETE":
        r = requests.delete(f"{BASE}{path}", headers=headers, timeout=10)
    else:
        fail(f"unsupported method in test: {method}")
        return
    if r.status_code not in expect_codes:
        fail(f"{label}: expected HTTP in {expect_codes}, got {r.status_code} — {r.text[:200]}")
    assert_no_leak_in_body(r.content, label)
    ok(f"{label} ({r.status_code})")


def check_admin_only_rejects_tenant(label: str, method: str, path: str, key_b: str) -> None:
    """Admin-only endpoints MUST reject a non-admin tenant key."""
    headers = auth(key_b)
    if method == "GET":
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=10)
    elif method == "DELETE":
        r = requests.delete(f"{BASE}{path}", headers=headers, timeout=10)
    elif method == "POST":
        r = requests.post(f"{BASE}{path}", headers=headers, json={}, timeout=10)
    else:
        fail(f"unsupported method: {method}")
        return
    if r.status_code in (200, 201, 202):
        fail(f"{label}: admin endpoint returned {r.status_code} to a tenant key — must be 401/403/503\n"
             f"Body: {r.text[:200]}")
    assert_no_leak_in_body(r.content, label, expect_status=r.status_code)
    ok(f"{label} (rejected with {r.status_code})")


# ── Cleanup ───────────────────────────────────────────────────────────────────

def revoke(key: str) -> None:
    """Best-effort cleanup; failure here is not test failure."""
    try:
        requests.delete(
            f"{BASE}/admin/api-keys/{key}",
            headers={"X-Admin-Token": ADMIN},
            timeout=5,
        )
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n=== Tenant isolation test against {BASE} ===\n", flush=True)

    step("waiting for /healthz")
    wait_healthy()

    step("creating tenant A and tenant B")
    key_a = create_key(label="iso-test-A")
    key_b = create_key(label="iso-test-B")
    ok(f"keys created: A={key_a[:10]}... B={key_b[:10]}...")

    try:
        step("populating tenant A with secrets")
        refs = populate_tenant_a(key_a)
        ok("tenant A populated (1 request, 1 trace+span, 1 budget, 1 instance)")

        # ── Per-endpoint isolation: tenant B must see NOTHING of A's data ──
        step("checking aggregations are tenant-scoped")
        check_endpoint_isolated("GET /requests/stats",       "GET", "/requests/stats",       key_b)
        check_endpoint_isolated("GET /requests/trend",       "GET", "/requests/trend",       key_b)
        check_endpoint_isolated("GET /requests/worst",       "GET", "/requests/worst",       key_b)
        check_endpoint_isolated("GET /requests/cost-quality","GET", "/requests/cost-quality",key_b)
        check_endpoint_isolated("GET /requests/regression",  "GET", "/requests/regression",  key_b)

        step("checking list endpoints are tenant-scoped")
        check_endpoint_isolated("GET /debug/requests",       "GET", "/debug/requests?limit=50", key_b)
        check_endpoint_isolated("GET /debug/models",         "GET", "/debug/models",         key_b)
        check_endpoint_isolated("GET /debug/flags",          "GET", "/debug/flags",          key_b)
        check_endpoint_isolated("GET /traces",               "GET", "/traces?limit=50",      key_b)
        check_endpoint_isolated("GET /portal/instances",     "GET", "/portal/instances",     key_b)

        step("checking detail-by-id rejects cross-tenant access (must be 404)")
        check_endpoint_isolated(
            "GET /traces/{A's trace_id}", "GET",
            f"/traces/{refs['trace_id']}", key_b, expect_codes={404, 403},
        )

        step("checking compliance export is tenant-scoped")
        check_endpoint_isolated("GET /compliance/export", "GET", "/compliance/export", key_b)

        step("checking budget alert is tenant-scoped (H3 regression)")
        # Tenant B should see EITHER no budget configured OR its own (empty) budget,
        # but NOT tenant A's webhook URL or email.
        r = requests.get(f"{BASE}/alerts/budget", headers=auth(key_b), timeout=10)
        if r.status_code != 200:
            fail(f"GET /alerts/budget returned {r.status_code} for tenant B")
        body = r.text
        assert_no_leak_in_body(body, "GET /alerts/budget")
        ok("GET /alerts/budget — no tenant-A webhook/email visible to tenant B")

        step("checking audit-log is admin-only (H1 regression)")
        check_admin_only_rejects_tenant("GET /compliance/audit-log",        "GET", "/compliance/audit-log",        key_b)
        check_admin_only_rejects_tenant("GET /compliance/audit-log/export", "GET", "/compliance/audit-log/export", key_b)

        step("checking admin routes reject tenant keys")
        check_admin_only_rejects_tenant("GET /admin/api-keys",              "GET", "/admin/api-keys",              key_b)
        check_admin_only_rejects_tenant("GET /admin/customers",             "GET", "/admin/customers",             key_b)

    finally:
        step("cleanup: revoking test keys")
        revoke(key_a)
        revoke(key_b)

    print("\n  PASS PASS PASS  TENANT ISOLATION GREEN  PASS PASS PASS\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
