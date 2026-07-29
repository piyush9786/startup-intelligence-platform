#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE=(docker compose -f docker-compose.yml)
if [[ -f docker-compose.llm.yml ]]; then
  COMPOSE+=( -f docker-compose.llm.yml )
fi

printf '%s\n' '=== AI readiness ==='
curl --fail --silent http://localhost:8000/api/v1/ai-readiness/ | python3 -m json.tool

printf '\n%s\n' '=== Installed Ollama models ==='
"${COMPOSE[@]}" exec -T ollama ollama list

printf '\n%s\n' '=== Models currently loaded ==='
"${COMPOSE[@]}" exec -T ollama ollama ps || true

printf '\n%s\n' '=== Container resource snapshot ==='
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' \
  startup_intelligence-ollama-1 \
  startup_intelligence-backend-1 \
  startup_intelligence-worker-1 2>/dev/null || true

printf '\n%s\n' '=== Integration check (without another long generation) ==='
"${COMPOSE[@]}" exec -T backend python manage.py llm_doctor --skip-generation
