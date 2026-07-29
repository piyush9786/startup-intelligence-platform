#!/usr/bin/env bash
set -Eeuo pipefail

USE_GPU=false
case "${1:-}" in
  --gpu) USE_GPU=true ;;
  "") ;;
  *) echo "Usage: $0 [--gpu]" >&2; exit 2 ;;
esac
export USE_GPU

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laptop_common.sh"

require_command docker
require_command curl
prepare_env

log "Stopping frontend before dependency-volume repair"
compose stop frontend >/dev/null 2>&1 || true
compose rm -f frontend >/dev/null 2>&1 || true

# This volume contains only npm dependencies. Removing it does not touch
# PostgreSQL, Redis, MinIO, Neo4j, Qdrant, Ollama models, or uploaded data.
FRONTEND_VOLUME="startup-intelligence_frontend_node_modules"
if docker volume inspect "${FRONTEND_VOLUME}" >/dev/null 2>&1; then
  log "Removing stale frontend dependency volume"
  docker volume rm "${FRONTEND_VOLUME}" >/dev/null
fi

log "Rebuilding the frontend image without cache"
compose build --no-cache frontend

if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
  compose up -d frontend
else
  warn "Backend is not healthy; starting the frontend without dependencies so startup errors remain visible."
  compose up -d --no-deps frontend
fi

log "Waiting for transformed frontend modules"
for attempt in $(seq 1 120); do
  modules_ok=true
  for module in bootstrap.js main.jsx App.jsx AppShell.jsx DashboardHome.jsx; do
    if ! curl --fail --silent "http://localhost:5173/src/${module}" >/dev/null 2>&1; then
      modules_ok=false
      break
    fi
  done
  if [[ "${modules_ok}" == "true" ]]; then
    printf '\nFrontend repair complete: http://localhost:5173\n'
    exit 0
  fi
  sleep 2
done

compose logs --tail=250 frontend
fail "Frontend modules did not become healthy. Review the log above."
