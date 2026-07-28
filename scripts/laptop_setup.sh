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

log "Building and starting the complete laptop stack"
compose up -d --build

log "Waiting for the backend and catalog bootstrap"
for attempt in $(seq 1 900); do
  if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 900 ]]; then
    compose ps
    compose logs --tail=200 ollama_init backend
    fail "Backend did not become healthy."
  fi
  sleep 2
done

log "Checking required scheme and support data"
compose exec -T backend python manage.py platform_doctor --strict

log "Waiting for the frontend"
for attempt in $(seq 1 120); do
  if curl --fail --silent http://localhost:5173/ >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 120 ]]; then
    compose ps
    compose logs --tail=200 frontend
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
