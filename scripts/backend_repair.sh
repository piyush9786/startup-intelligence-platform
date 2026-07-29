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

log "Starting required infrastructure"
compose up -d postgres redis qdrant neo4j minio minio_init ollama ollama_init mailpit

log "Rebuilding and recreating the backend"
compose stop backend worker beat >/dev/null 2>&1 || true
compose rm -f backend worker beat >/dev/null 2>&1 || true
compose build --no-cache backend
compose up -d backend

log "Waiting for the backend health endpoint"
for attempt in $(seq 1 180); do
  if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 180 ]]; then
    compose ps
    compose logs --tail=300 backend
    fail "Backend did not become healthy. The backend log above contains the root cause."
  fi
  sleep 2
done

log "Importing and validating bundled scheme, funding, and requirement catalogs"
if ! compose run --rm catalog_init; then
  compose logs --tail=300 backend
  fail "Catalog initialization failed. The API remains available; review the command error above."
fi

log "Starting workers and frontend"
compose up -d worker beat frontend

log "Checking frontend modules"
for attempt in $(seq 1 120); do
  modules_ok=true
  for module in bootstrap.js main.jsx App.jsx AppShell.jsx DashboardHome.jsx; do
    if ! curl --fail --silent "http://localhost:5173/src/${module}" >/dev/null 2>&1; then
      modules_ok=false
      break
    fi
  done
  if [[ "${modules_ok}" == "true" ]]; then
    printf '\nRepair complete:\n  Frontend: http://localhost:5173\n  Backend:  http://localhost:8000/api/v1/health/\n'
    exit 0
  fi
  sleep 2
done

compose logs --tail=250 frontend
fail "Frontend did not become healthy. Review the frontend log above."
