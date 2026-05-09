#!/usr/bin/env bash
# AgentLens — Self-host uninstaller.
#
# Default behaviour: stops + removes the container. KEEPS your data volume.
# Use --purge to also delete the data volume (irreversible).
#
# Usage:
#   curl -fsSL https://www.agentlens.one/uninstall.sh | bash
#   curl -fsSL https://www.agentlens.one/uninstall.sh | bash -s -- --purge
#
# Reads config from $HOME/.agentlens/.env if present (set by install.sh).

set -Eeuo pipefail

PURGE=false
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=true ;;
    -h|--help)
      cat <<HELP
AgentLens uninstaller

  --purge   Also delete the data volume (irreversible — your traces are gone).
            Without this flag, the volume is preserved so you can re-install later.
  -h        Show this help.
HELP
      exit 0
      ;;
    *) ;;
  esac
done

# ── Load config if available ──────────────────────────────────────────────────
HOME_DIR="${AGENTLENS_HOME:-$HOME/.agentlens}"
ENV_FILE="$HOME_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$ENV_FILE"; set +a
fi

CONTAINER_NAME="${AGENTLENS_CONTAINER:-agentlens}"
DATA_VOLUME="${AGENTLENS_VOLUME:-agentlens-data}"

# ── Pretty output ─────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; BLUE=''; BOLD=''; NC=''
fi

ok()   { printf "  ${GREEN}✓${NC} %s\n" "$*"; }
info() { printf "  ${BLUE}→${NC} %s\n" "$*"; }
warn() { printf "  ${YELLOW}!${NC} %s\n" "$*"; }

cat <<EOF

  ${BOLD}AgentLens${NC} uninstaller
  ─────────────────────────
  Container:  $CONTAINER_NAME
  Volume:     $DATA_VOLUME
  Purge:      $($PURGE && echo "yes (data DELETED)" || echo "no (data kept)")

EOF

command -v docker >/dev/null 2>&1 || { warn "Docker not found — nothing to uninstall."; exit 0; }

# ── Stop + remove container ───────────────────────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  info "Stopping container..."
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true
  ok "Container removed."
else
  info "Container '$CONTAINER_NAME' not found — skipping."
fi

# ── Volume (only with --purge) ────────────────────────────────────────────────
if $PURGE; then
  if docker volume ls --format '{{.Name}}' | grep -qx "$DATA_VOLUME"; then
    if [[ -t 0 ]]; then
      warn "About to permanently delete volume '$DATA_VOLUME' (all SQLite data, all traces)."
      read -rp "  Type 'PURGE' to confirm: " confirm
      if [[ "$confirm" != "PURGE" ]]; then
        warn "Aborted volume deletion. Volume preserved."
      else
        docker volume rm "$DATA_VOLUME" >/dev/null
        ok "Volume removed."
      fi
    else
      # Non-interactive: --purge alone is enough.
      docker volume rm "$DATA_VOLUME" >/dev/null && ok "Volume removed."
    fi
  else
    info "Volume '$DATA_VOLUME' not found — skipping."
  fi
else
  info "Volume '$DATA_VOLUME' preserved. Re-install will reuse it. Pass --purge to delete."
fi

# ── Remove local config ───────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  if $PURGE; then
    rm -f "$ENV_FILE"
    rmdir "$HOME_DIR" 2>/dev/null || true
    ok "Removed config $ENV_FILE"
  else
    info "Config $ENV_FILE preserved. Pass --purge to delete it too."
  fi
fi

cat <<EOF

  ${GREEN}✓ Uninstall complete.${NC}

  To re-install:
      curl -fsSL https://www.agentlens.one/install | bash

EOF
