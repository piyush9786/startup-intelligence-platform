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
require_command python3

log "Container status"
compose ps

log "HTTP health"
curl --fail --silent http://localhost:8000/api/v1/health/ | python3 -m json.tool
curl --fail --silent http://localhost:8000/api/v1/status/ | python3 -m json.tool

log "Catalog health"
compose exec -T backend python manage.py platform_doctor --strict

log "Frontend health"
for module in bootstrap.js main.jsx App.jsx AppShell.jsx DashboardHome.jsx; do
  curl --fail --silent "http://localhost:5173/src/${module}" >/dev/null
done
printf 'frontend_html=ok frontend_modules=ok\n'

if [[ "${USE_GPU}" == "true" ]]; then
  log "GPU and Ollama"
  nvidia-smi
  compose exec -T ollama ollama ps || true
fi
