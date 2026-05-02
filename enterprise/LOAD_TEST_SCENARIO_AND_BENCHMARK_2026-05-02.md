# Load Test Scenario and Benchmark Run

Stand: 2026-05-02
Owner: Engineering
Status: completed (baseline run)

## 1. Scenario Definition (v1)
- Goal: collect baseline latency and availability under repeated synthetic requests.
- Target endpoints:
  - Primary availability baseline: `https://www.agentlens.one/`
  - Health endpoint validation target: `https://www.agentlens.one/healthz`
- Method:
  - Sequential HTTP requests with timeout guard
  - Collect success rate, p50, p95, max latency

## 2. Benchmark Run A (Landing URL)
- Endpoint: `https://www.agentlens.one/`
- Requests: 50
- Success: 50/50 (100%)
- p50 latency: 130.65 ms
- p95 latency: 184.62 ms
- max latency: 255.67 ms

## 3. Benchmark Run B (Health URL check)
- Endpoint: `https://www.agentlens.one/healthz`
- Requests: 20
- Success: 0/20
- Error type: HTTPError responses
- Interpretation:
  - Current live deployment did not expose `/healthz` at measurement time.
  - New health endpoints are available in current codebase and should be re-verified post-deploy.

## 4. Follow-up Actions
- Deploy current code containing `/healthz`, `/readyz`, `/health`.
- Re-run benchmark against `/healthz` after deployment and append results.
