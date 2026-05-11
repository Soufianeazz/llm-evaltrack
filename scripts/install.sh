#!/usr/bin/env bash
# AgentLens — One-line self-host installer.
#
# Quick run:
#   curl -fsSL https://www.agentlens.one/install | bash
#
# Deterministic / unattended:
#   AGENTLENS_LABEL=veritasgraph AGENTLENS_PORT=8000 \
#     curl -fsSL https://www.agentlens.one/install | bash
#
# What it does:
#   1. Verifies Linux + Docker
#   2. Pulls the pinned AgentLens image
#   3. Generates a strong ADMIN_TOKEN locally (never sent anywhere)
#   4. Starts the container with AGENTLENS_AIRGAP=1 (no outbound calls)
#   5. Waits for /healthz
#   6. Creates a tenant API key inside the local DB
#   7. Prints dashboard URL + API key + SDK snippet
#
# This script makes ZERO calls to agentlens.one. All operations are local.

set -Eeuo pipefail

# ── Config (override via env) ─────────────────────────────────────────────────
IMAGE="${AGENTLENS_IMAGE:-ghcr.io/soufianeazz/agentlens:pilot-latest}"
CONTAINER_NAME="${AGENTLENS_CONTAINER:-agentlens}"
PORT="${AGENTLENS_PORT:-8000}"
DATA_VOLUME="${AGENTLENS_VOLUME:-agentlens-data}"
LABEL="${AGENTLENS_LABEL:-pilot}"
PLAN="${AGENTLENS_PLAN:-pilot}"
ROLE="${AGENTLENS_ROLE:-admin}"
HOME_DIR="${AGENTLENS_HOME:-$HOME/.agentlens}"
HEALTH_TIMEOUT="${AGENTLENS_HEALTH_TIMEOUT:-90}"

# ── Pretty output ─────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

ok()   { printf "  ${GREEN}✓${NC} %s\n" "$*"; }
info() { printf "  ${BLUE}→${NC} %s\n" "$*"; }
warn() { printf "  ${YELLOW}!${NC} %s\n" "$*"; }
fail() { printf "\n  ${RED}✗ %s${NC}\n\n" "$*" >&2; exit 1; }

trap 'fail "Install failed at line $LINENO. Check output above."' ERR

cat <<EOF

  ${BOLD}AgentLens${NC} self-host installer
  ─────────────────────────────────
  Image:     $IMAGE
  Container: $CONTAINER_NAME
  Port:      $PORT
  Label:     $LABEL

EOF

# ── Pre-flight checks ─────────────────────────────────────────────────────────
[[ "$(uname -s)" == "Linux" ]] || fail "This installer supports Linux only. macOS/Windows users: see docs/SELF_HOST.md for manual instructions."

command -v docker >/dev/null 2>&1 || fail "Docker not found. Install Docker first: https://docs.docker.com/engine/install/"
docker info >/dev/null 2>&1 || fail "Docker daemon not running or your user lacks permission. Try: sudo systemctl start docker, then re-run."

command -v curl >/dev/null 2>&1 || fail "curl not found. Install with: apt install -y curl"

ok "Linux + Docker detected"

# ── Generate admin token locally ──────────────────────────────────────────────
ADMIN_TOKEN="$(LC_ALL=C tr -dc 'A-Za-z0-9_-' < /dev/urandom 2>/dev/null | head -c 48 || echo "fallback-$(date +%s%N)-$$")"
[[ ${#ADMIN_TOKEN} -ge 32 ]] || fail "Failed to generate admin token (need /dev/urandom)."

# ── Replace any existing container with confirmation ──────────────────────────
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  warn "Container '$CONTAINER_NAME' already exists."
  if [[ -t 0 ]]; then
    read -rp "  Stop and replace it? Existing data on volume '$DATA_VOLUME' is preserved. (y/N) " -n 1 -r REPLY
    echo
    [[ "$REPLY" =~ ^[Yy]$ ]] || fail "Aborted by user."
  else
    info "Non-interactive mode — replacing existing container automatically."
  fi
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# ── Pull image ────────────────────────────────────────────────────────────────
info "Pulling image (this may take a minute on first run)..."
docker pull "$IMAGE" >/dev/null || fail "Failed to pull '$IMAGE'. Check that ghcr.io is reachable."
ok "Image ready"

# ── Volume + container ────────────────────────────────────────────────────────
docker volume create "$DATA_VOLUME" >/dev/null
ok "Volume '$DATA_VOLUME' ready"

info "Starting AgentLens container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "${DATA_VOLUME}:/data" \
  -e AGENTLENS_AIRGAP=1 \
  -e ADMIN_TOKEN="$ADMIN_TOKEN" \
  -e DATABASE_URL="sqlite+aiosqlite:////data/agentlens.db" \
  "$IMAGE" >/dev/null

# ── Wait for healthz ──────────────────────────────────────────────────────────
info "Waiting for AgentLens to be ready (timeout ${HEALTH_TIMEOUT}s)..."
deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
ready=false
while [[ $(date +%s) -lt $deadline ]]; do
  if curl -fsS --max-time 2 "http://localhost:${PORT}/healthz" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done

if ! $ready; then
  warn "Container did not become healthy in ${HEALTH_TIMEOUT}s. Last 50 lines of logs:"
  docker logs --tail 50 "$CONTAINER_NAME" >&2 || true
  fail "Startup failed. Container left running for inspection. Run: docker logs $CONTAINER_NAME"
fi
ok "AgentLens is healthy on http://localhost:${PORT}"

# ── Bootstrap an API key for the SDK ──────────────────────────────────────────
info "Creating your tenant API key inside the local container..."
KEY_RESPONSE="$(curl -fsS \
  -X POST "http://localhost:${PORT}/admin/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"label\":\"${LABEL}\",\"plan\":\"${PLAN}\",\"role\":\"${ROLE}\"}")" \
  || fail "Failed to create API key. Run: docker logs $CONTAINER_NAME"

API_KEY="$(printf '%s' "$KEY_RESPONSE" | sed -n 's/.*"key"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
[[ -n "$API_KEY" ]] || fail "Could not parse API key from server response: $KEY_RESPONSE"
ok "API key created (label: $LABEL)"

# ── Persist config locally ────────────────────────────────────────────────────
mkdir -p "$HOME_DIR"
chmod 700 "$HOME_DIR"
ENV_FILE="$HOME_DIR/.env"
{
  echo "# AgentLens — written by install.sh on $(date -u +%FT%TZ)"
  echo "# This file holds local-only secrets. Do NOT commit it."
  echo "AGENTLENS_CONTAINER=$CONTAINER_NAME"
  echo "AGENTLENS_PORT=$PORT"
  echo "AGENTLENS_VOLUME=$DATA_VOLUME"
  echo "AGENTLENS_IMAGE=$IMAGE"
  echo "AGENTLENS_LABEL=$LABEL"
  echo "ADMIN_TOKEN=$ADMIN_TOKEN"
  echo "AGENTLENS_API_KEY=$API_KEY"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok "Config saved to $ENV_FILE (chmod 600)"

# ── Detect a reachable host IP for the user's SDK config ──────────────────────
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
HOST_IP="${HOST_IP:-localhost}"

# ── Final summary ─────────────────────────────────────────────────────────────
cat <<EOF

  ${GREEN}═══════════════════════════════════════════════════════════════════════${NC}
  ${BOLD}${GREEN}  ✓ AgentLens is running.${NC}
  ${GREEN}═══════════════════════════════════════════════════════════════════════${NC}

  ${BOLD}Dashboard${NC}     http://${HOST_IP}:${PORT}
  ${BOLD}Health${NC}        http://${HOST_IP}:${PORT}/healthz

  ${BOLD}Your API key${NC}  (save this — it won't be shown again):

      ${YELLOW}${API_KEY}${NC}

  ${BOLD}Add this to your code${NC}:

      import agentlens
      agentlens.init(
          api_url="http://${HOST_IP}:${PORT}/ingest",
          api_key="${API_KEY}",
      )
      agentlens.patch_openai()  # also covers Ollama (OpenAI-compatible API)

  ${BOLD}Container management${NC}:
      docker logs -f $CONTAINER_NAME      # follow logs
      docker stop  $CONTAINER_NAME        # stop
      docker start $CONTAINER_NAME        # restart
      curl -fsSL https://www.agentlens.one/uninstall | bash

  ${BOLD}Air-gap status${NC}    ${GREEN}✓ enabled${NC}  (no outbound calls — verify with: tcpdump -i any 'not port ${PORT}')
  ${BOLD}Config${NC}            $ENV_FILE
  ${BOLD}Data volume${NC}       $DATA_VOLUME

  ${BOLD}Next${NC}: register this instance on https://www.agentlens.one/app/deploy
        so we can support you during the pilot. Paste the API key above.

EOF
