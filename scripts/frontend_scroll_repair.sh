#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f docker-compose.yml || ! -f frontend/package.json ]]; then
  echo "Run this script from the startup-intelligence-platform project." >&2
  exit 1
fi

compose=(docker compose)
if [[ "${1:-}" == "--gpu" ]]; then
  compose=(docker compose -f docker-compose.yml -f docker-compose.gpu.yml)
fi

printf '\n==> Rebuilding the frontend scroll fix\n'
"${compose[@]}" stop frontend >/dev/null 2>&1 || true
"${compose[@]}" build frontend
"${compose[@]}" up -d frontend

printf '\n==> Waiting for Vite and the scroll manager module\n'
for attempt in $(seq 1 60); do
  if curl -fsS http://localhost:5173/src/RouteScrollManager.jsx >/dev/null 2>&1; then
    printf '\nFrontend scroll repair complete: http://localhost:5173\n'
    printf 'Use Ctrl+Shift+R once, then route changes and reloads should start at the top.\n'
    exit 0
  fi
  sleep 2
done

printf '\nFrontend did not expose the repaired module in time. Recent logs:\n' >&2
"${compose[@]}" logs --tail=160 frontend >&2 || true
exit 1
