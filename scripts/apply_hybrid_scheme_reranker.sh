#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

compose=(docker compose)

say() {
  printf '\n==> %s\n' "$*"
}

wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"
  local delay="${3:-2}"

  for ((i=1; i<=attempts; i++)); do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done

  printf 'Timed out waiting for %s\n' "$url" >&2
  return 1
}

say "Validating hotfix files"
required=(
  backend/apps/schemes/services/hybrid_search.py
  backend/apps/schemes/views.py
  backend/apps/schemes/tests/test_hybrid_search.py
  frontend/src/SchemeExplorerPage.jsx
  frontend/src/api.js
)
for file in "${required[@]}"; do
  if [[ ! -f "$file" ]]; then
    printf 'Missing required file: %s\n' "$file" >&2
    exit 1
  fi
done

python3 -m py_compile \
  backend/apps/schemes/services/hybrid_search.py \
  backend/apps/schemes/views.py \
  backend/apps/schemes/tests/test_hybrid_search.py

node --check frontend/src/api.js

say "Starting required services"
"${compose[@]}" up -d postgres redis minio minio_init ollama ollama_init

say "Rebuilding Django and React images"
"${compose[@]}" build backend frontend

say "Starting application services"
"${compose[@]}" up -d backend worker beat frontend

say "Waiting for backend and frontend"
wait_for_url "http://localhost:8000/api/v1/health/" 90 2
wait_for_url "http://localhost:5173" 90 2

say "Running Django checks and hybrid-ranking tests"
"${compose[@]}" exec -T backend python manage.py check
"${compose[@]}" exec -T backend \
  python manage.py test apps.schemes.tests.test_hybrid_search --verbosity 1

say "Testing the public hybrid-search endpoint"
response="$(curl --fail --silent --show-error --get \
  --data-urlencode 'q=biotechnology innovation grant' \
  --data-urlencode 'limit=5' \
  http://localhost:8000/api/v1/schemes/hybrid-search/)"

python3 - "$response" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required = {
    "ranking_version",
    "detected_intents",
    "model",
    "no_match",
    "results",
}
missing = sorted(required - payload.keys())
if missing:
    raise SystemExit(f"Hybrid endpoint is missing fields: {missing}")

print("ranking_version=" + str(payload["ranking_version"]))
print("tfidf_version=" + str(payload.get("model", {}).get("version")))
print("result_count=" + str(len(payload.get("results", []))))
if payload.get("results"):
    print("top_result=" + str(payload["results"][0].get("scheme_name")))
else:
    print("message=" + str(payload.get("message", "")))
PY

say "Hybrid scheme reranker is ready"
printf '%s\n' \
  'Open http://localhost:5173/schemes' \
  'Use Ctrl+Shift+R once, then try:' \
  '  biotechnology innovation grant' \
  '  loan support for manufacturing MSME' \
  '  women entrepreneur government scheme'
