# Pre-Pilot Dry-Run Runbook

**Purpose:** Before Bibin (or any pilot customer) gets the install command, **you** run the
exact same flow on a fresh Linux VM that has never seen AgentLens. If anything breaks here,
fix it BEFORE the customer touches it.

**Time budget:** 60 minutes (45 min if Docker is pre-installed).

**Pass criteria:** All 8 checkpoints below return ✓ on the first attempt.

---

## 0 · Prerequisites on your laptop

- [ ] DigitalOcean / Hetzner / AWS / any provider account
- [ ] SSH key uploaded
- [ ] `agentlens.one` deploy is on the smoke-tested image tag (check GitHub Actions → "Release Pilot Image" → green)

## 1 · Spin up a fresh Ubuntu VM

DigitalOcean (recommended for cheapness — destroy after run):

```bash
# Via doctl, or just click "Create Droplet" in UI:
#   - Image:  Ubuntu 22.04 LTS
#   - Size:   Basic / 1 GB RAM / 1 vCPU / $4 mo  (s-1vcpu-1gb)
#   - Region: closest to you
#   - SSH:    your key
```

Save the public IP as `$VM_IP`.

```bash
export VM_IP=xxx.xxx.xxx.xxx
ssh root@$VM_IP
```

## 2 · Install Docker (if needed)

```bash
# Inside the VM:
apt-get update -y
apt-get install -y curl
curl -fsSL https://get.docker.com | sh
docker --version  # → Docker version 24.x or higher
```

✅ **Checkpoint 1:** `docker info` runs without error.

## 3 · Run the AgentLens installer (the EXACT one-liner Bibin will run)

```bash
# Inside the VM, as root or a sudo user:
curl -fsSL https://www.agentlens.one/install | bash
```

✅ **Checkpoint 2:** Installer prints the green box `✓ AgentLens is running.`
   - Note the API key it shows (you'll need it in step 5).
   - Note the dashboard URL.

✅ **Checkpoint 3:** Time-to-green is under **3 minutes** total (image pull + startup).
   If slower, investigate before exposing this to a customer.

## 4 · Verify the dashboard from your laptop

```bash
# From your laptop:
curl -fsS http://$VM_IP:8000/healthz  # → {"status":"ok",...}
open http://$VM_IP:8000               # macOS
# or visit http://$VM_IP:8000 in your browser
```

✅ **Checkpoint 4:** Dashboard loads. Demo-Key data is visible (from `seed_demo_on_startup`).

## 5 · Verify air-gap with tcpdump

This is the **most important check** — Bibin's reason for self-host.

```bash
# Back inside the VM, in a second SSH session:
apt-get install -y tcpdump
tcpdump -nni any 'not port 22 and not port 8000 and not arp and not (host 127.0.0.1)' -c 50
```

In the meantime trigger ingest from a third terminal (also inside the VM):

```bash
# Use the API key from step 3 — paste it as $KEY:
export KEY="al_PASTE_YOUR_KEY"
for i in $(seq 1 5); do
  curl -fsS -X POST http://localhost:8000/ingest \
    -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -d "{\"input\":\"test $i\",\"output\":\"reply $i\",\"prompt\":\"You are a helper\",\"model\":\"gpt-4o-mini\",\"metadata\":{\"input_tokens\":10,\"output_tokens\":5,\"cost_usd\":0.0001}}"
  echo
done
```

✅ **Checkpoint 5:** tcpdump catches **ZERO packets** (timeout after 30s with no output).
   - This proves: no Anthropic, no Stripe, no Resend, no telemetry.
   - If you see ANY traffic — STOP. Investigate before Bibin touches this.

## 6 · Test the Python SDK end-to-end

```bash
# Inside the VM:
apt-get install -y python3-pip
pip3 install agentlens-monitor

cat > /tmp/sdk_test.py <<'PY'
import os, agentlens
agentlens.init(
    api_url="http://localhost:8000/ingest",
    api_key=os.environ["KEY"],
)
agentlens.track_llm_call(
    input_text="what is 2+2",
    output_text="4",
    prompt_template="answer math questions",
    model="gpt-4o-mini",
    metadata={"input_tokens": 10, "output_tokens": 1, "cost_usd": 0.00005},
)
print("✓ SDK ingest fired")

# Trace test
from agentlens import trace_agent
with trace_agent("test_agent", input="hello") as t:
    with t.span("step1", span_type="llm", model="gpt-4o") as s:
        s.set_output("response")
        s.set_tokens(50)
    t.set_output("done")
print("✓ trace_agent fired")
PY

KEY=$KEY python3 /tmp/sdk_test.py
sleep 3
curl -fsS "http://localhost:8000/requests/stats" -H "X-API-Key: $KEY"
```

✅ **Checkpoint 6:** `requests/stats` shows at least 1 call within 24h.

## 7 · Test the Deploy page round-trip

On your laptop browser:
1. Visit https://www.agentlens.one/app, sign up with a test account.
2. Get approved (or auto-approve via admin if dry-run user).
3. Visit https://www.agentlens.one/app/deploy.
4. Register a fake instance: label "dry-run-test", check "14-day pilot".
5. Confirm it appears in "Your registered instances".
6. Remove it via the "Remove" link.

✅ **Checkpoint 7:** Register/list/delete cycle works from the browser without errors.

## 8 · Test uninstall

```bash
# Inside the VM:
curl -fsSL https://www.agentlens.one/uninstall | bash
docker ps -a | grep agentlens   # → no rows
docker volume ls | grep agentlens  # → volume preserved (no --purge flag)

# Re-install
curl -fsSL https://www.agentlens.one/install | bash
# Should detect existing volume and reuse it
```

✅ **Checkpoint 8:** Re-install reuses the volume; previous data still visible in dashboard.

## 9 · Tear down the dry-run VM

Once all 8 checkpoints pass:

```bash
# Destroy the VM via your provider UI (or doctl)
doctl compute droplet delete <id>
```

---

## What to do if a checkpoint fails

| Failure | Diagnosis path |
|---|---|
| Checkpoint 1 (Docker) | `journalctl -xeu docker.service` — usually a kernel/user-namespace issue |
| Checkpoint 2 (installer) | Re-run with `bash -x`: `curl -fsSL https://www.agentlens.one/install \| bash -x` |
| Checkpoint 3 (slow) | Check image size: `docker images ghcr.io/soufianeazz/agentlens` — should be < 200 MB |
| Checkpoint 4 (dashboard) | Firewall: `ufw status`, ensure port 8000 allowed |
| Checkpoint 5 (tcpdump shows traffic) | **STOP.** Check `evaluation/engine.py` — is `AGENTLENS_AIRGAP=1` actually being read? Inspect container env: `docker exec agentlens env \| grep AIRGAP` |
| Checkpoint 6 (SDK ingest fails) | `docker logs agentlens` — check for evaluation worker errors |
| Checkpoint 7 (deploy page) | Browser console errors; check `/portal/instances` returns 200 with correct X-API-Key |
| Checkpoint 8 (re-install fails) | Volume contention; document the manual recovery and fix in install.sh |

## Sign-off

Once all 8 checkpoints pass, mark the pilot image as **promoted to pilot tag**:

```bash
# Trigger workflow_dispatch on .github/workflows/release-pilot-image.yml
# with input pilot_tag = "pilot-2026.05.12"  (or whatever date)
gh workflow run release-pilot-image.yml -f pilot_tag=pilot-2026.05.12
```

Then update Bibin's instructions to pin to that tag:

```bash
AGENTLENS_IMAGE=ghcr.io/soufianeazz/agentlens:pilot-2026.05.12 \
  curl -fsSL https://www.agentlens.one/install | bash
```

This way, if you push changes to main during the 14-day pilot, Bibin's container is unaffected.
