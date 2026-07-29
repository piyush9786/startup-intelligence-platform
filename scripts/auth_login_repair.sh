#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f docker-compose.yml || ! -f .env ]]; then
  echo "Run this script inside the startup-intelligence-platform project." >&2
  exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"
cp .env ".env.auth-repair-${stamp}.bak"

echo "==> Normalizing Docker-internal Redis and Celery addresses"
python3 - <<'PY'
from pathlib import Path

path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines()
required = {
    'REDIS_URL': 'redis://redis:6379/0',
    'CELERY_BROKER_URL': 'redis://redis:6379/1',
    'CELERY_RESULT_BACKEND': 'redis://redis:6379/2',
}
seen = set()
out = []
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0].strip()
        if key in required:
            out.append(f'{key}={required[key]}')
            seen.add(key)
            continue
    out.append(line)
for key, value in required.items():
    if key not in seen:
        out.append(f'{key}={value}')
path.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')
PY

echo "==> Starting PostgreSQL and Redis"
docker compose up -d postgres redis

for attempt in $(seq 1 30); do
  postgres_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' startup_intelligence-postgres-1 2>/dev/null || true)"
  redis_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' startup_intelligence-redis-1 2>/dev/null || true)"
  if [[ "$postgres_status" == "healthy" && "$redis_status" == "healthy" ]]; then
    break
  fi
  sleep 2
done

echo "==> Clearing only Redis database 0 used by Django cache/rate limits"
docker compose exec -T redis redis-cli -n 0 FLUSHDB >/dev/null

echo "==> Applying account, session, and JWT blacklist migrations"
if docker compose ps --status running --services | grep -qx backend; then
  docker compose exec -T backend python manage.py migrate --noinput
  docker compose exec -T backend python manage.py check
else
  docker compose run --rm --no-deps backend python manage.py migrate --noinput
  docker compose run --rm --no-deps backend python manage.py check
fi

echo "==> Recreating backend, worker, and beat with corrected environment"
docker compose up -d --force-recreate backend

for attempt in $(seq 1 60); do
  if curl -fsS http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
  echo "Backend did not become healthy. Recent logs:" >&2
  docker compose logs --tail=250 backend >&2 || true
  exit 1
fi

docker compose up -d --force-recreate worker beat frontend

echo "==> Testing the login endpoint with intentionally invalid credentials"
status="$(curl -sS -o /tmp/startup-auth-diagnostic.json -w '%{http_code}' \
  -X POST http://localhost:8000/api/v1/auth/token/ \
  -H 'Content-Type: application/json' \
  --data '{"username":"__startup_auth_diagnostic__","password":"not-a-real-password"}')"

case "$status" in
  401)
    echo
    echo "Authentication endpoint is healthy (invalid credentials correctly returned 401)."
    echo "Try your real username and password again at http://localhost:5173"
    echo "Use Ctrl+Shift+R once before signing in."
    ;;
  429)
    echo
    echo "Authentication endpoint is working but rate-limited (429)."
    echo "Wait one minute, then try again."
    ;;
  *)
    echo
    echo "Authentication endpoint still returned HTTP ${status}. Response:" >&2
    cat /tmp/startup-auth-diagnostic.json >&2 || true
    echo >&2
    echo "Recent backend traceback:" >&2
    docker compose logs --tail=300 backend >&2 || true
    exit 1
    ;;
esac

echo
echo "Environment backup: .env.auth-repair-${stamp}.bak"
