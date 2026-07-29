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
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
prepare_env

if [[ "${USE_GPU}" == "true" ]]; then
  require_command nvidia-smi
  nvidia-smi >/dev/null || fail "The NVIDIA driver is not working."
  log "NVIDIA GPU mode enabled for Ollama"
fi

log "Removing stale frontend dependency container and volume"
compose stop frontend >/dev/null 2>&1 || true
compose rm -f frontend >/dev/null 2>&1 || true
docker volume rm startup-intelligence_frontend_node_modules >/dev/null 2>&1 || true

log "Building application images"
compose build backend frontend

log "Starting infrastructure and API"
compose up -d postgres redis qdrant neo4j minio minio_init ollama ollama_init mailpit backend

log "Waiting for backend migrations and health"
for attempt in $(seq 1 300); do
  if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 300 ]]; then
    compose ps
    compose logs --tail=300 backend
    fail "Backend did not become healthy."
  fi
  sleep 2
done

log "Initializing bundled catalogs after the API is healthy"
compose run --rm catalog_init

log "Checking required scheme and support data"
compose exec -T backend python manage.py platform_doctor --strict

log "Starting workers and frontend"
compose up -d worker beat frontend

log "Waiting for the frontend"
for attempt in $(seq 1 120); do
  modules_ok=true
  for module in bootstrap.js main.jsx App.jsx AppShell.jsx DashboardHome.jsx; do
    if ! curl --fail --silent "http://localhost:5173/src/${module}" >/dev/null 2>&1; then
      modules_ok=false
      break
    fi
  done
  if [[ "${modules_ok}" == "true" ]]; then
    break
  fi
  if [[ "${attempt}" -eq 120 ]]; then
    compose ps
    compose logs --tail=250 frontend
    fail "Frontend did not become healthy."
  fi
  sleep 2
done

log "Laptop setup complete"
printf '%s\n' \
  'Web application: http://localhost:5173' \
  'API documentation: http://localhost:8000/api/docs/' \
  'Django admin: http://localhost:8000/admin/' \
  'Mailpit: http://localhost:8025' \
  'MinIO: http://localhost:9001' \
  'Qdrant: http://localhost:6333/dashboard' \
  'Neo4j: http://localhost:7474'
printf '\nCreate an account in the web app, or run: ./scripts/create_local_admin.sh\n'
