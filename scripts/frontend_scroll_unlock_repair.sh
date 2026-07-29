#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f docker-compose.yml || ! -f frontend/package.json ]]; then
  echo "Run this script inside the startup-intelligence-platform project." >&2
  exit 1
fi

printf '\n==> Rebuilding the frontend with one-shot scroll restoration\n'
docker compose stop frontend >/dev/null 2>&1 || true
docker compose build frontend
docker compose up -d --no-deps frontend

printf '\n==> Waiting for the repaired frontend modules\n'
for attempt in $(seq 1 60); do
  if curl -fsS http://localhost:5173/src/RouteScrollManager.jsx >/dev/null 2>&1 \
    && curl -fsS http://localhost:5173/src/App.jsx >/dev/null 2>&1; then
    printf '\nFrontend repair complete: http://localhost:5173\n'
    printf 'Normal scrolling is enabled. The Founder Operations Center launcher is removed.\n'
    printf 'Use Ctrl+Shift+R once after opening the page.\n'
    exit 0
  fi
  sleep 2
done

printf '\nFrontend did not expose the repaired modules in time. Recent logs:\n' >&2
docker compose logs --tail=180 frontend >&2 || true
exit 1
