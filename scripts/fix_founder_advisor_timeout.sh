#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\n\033[1;33mWARNING: %s\033[0m\n' "$*" >&2; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker is required."
command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v python3 >/dev/null 2>&1 || fail "python3 is required."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
[[ -f docker-compose.yml ]] || fail "Run this from the project root."
[[ -f .env ]] || fail ".env is missing."

MODEL="qwen3:4b-instruct-2507-q4_K_M"
STAMP="$(date +%Y%m%d-%H%M%S)"
cp .env ".env.before-advisor-timeout-fix-${STAMP}"

log "Writing the CPU-fast Founder Adviser profile"
python3 - <<'PY'
from pathlib import Path

path = Path('.env')
text = path.read_text(encoding='utf-8').splitlines()
values = {
    'STARTUP_ADVISOR_LLM_PROVIDER': 'ollama',
    'OLLAMA_BASE_URL': 'http://ollama:11434',
    'STARTUP_ADVISOR_LLM_MODEL': 'qwen3:4b-instruct-2507-q4_K_M',
    'CHATBOT_LLM_MODEL': 'qwen3:4b-instruct-2507-q4_K_M',
    'OLLAMA_CONTEXT_LENGTH': '4096',
    'OLLAMA_NUM_PARALLEL': '1',
    'OLLAMA_MAX_LOADED_MODELS': '2',
    'OLLAMA_MAX_QUEUE': '16',
    'STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS': '420',
    'STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS': '900',
    'STARTUP_ADVISOR_LLM_TEMPERATURE': '0.30',
    'STARTUP_ADVISOR_LLM_SEED': '7',
    'STARTUP_ADVISOR_LLM_KEEP_ALIVE': '30m',
    'STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS': '720',
    'STARTUP_ADVISOR_TASK_TIME_LIMIT_SECONDS': '780',
    'STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS': '900',
    'STARTUP_ADVISOR_RAG_ENABLED': 'true',
    'STARTUP_ADVISOR_RAG_TOP_K': '2',
    'STARTUP_ADVISOR_RAG_MAX_PROMPT_DOCUMENTS': '2',
    'STARTUP_ADVISOR_RAG_MAX_CHARS_PER_CHUNK': '650',
    'STARTUP_ADVISOR_RAG_MAX_TOTAL_CHARS': '1300',
    'STARTUP_ADVISOR_EMBEDDING_MODEL': 'embeddinggemma',
    'STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS': '90',
    'CELERY_WORKER_CONCURRENCY': '1',
}

result = []
seen = set()
for line in text:
    stripped = line.lstrip()
    key = line.split('=', 1)[0] if '=' in line and not stripped.startswith('#') else None
    if key in values:
        if key not in seen:
            result.append(f'{key}={values[key]}')
            seen.add(key)
    else:
        result.append(line)

if result and result[-1] != '':
    result.append('')
for key, value in values.items():
    if key not in seen:
        result.append(f'{key}={value}')

path.write_text('\n'.join(result).rstrip() + '\n', encoding='utf-8')
PY

COMPOSE=(docker compose)
if [[ -f docker-compose.llm.yml ]]; then
  COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.llm.yml)
fi

"${COMPOSE[@]}" config --quiet

log "Starting Ollama"
"${COMPOSE[@]}" up -d ollama

log "Waiting for Ollama"
for attempt in $(seq 1 120); do
  if curl --fail --silent http://localhost:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 120 ]]; then
    "${COMPOSE[@]}" logs --tail=250 ollama
    fail "Ollama did not become ready."
  fi
  sleep 2
done

log "Pulling the faster adviser model: ${MODEL}"
"${COMPOSE[@]}" exec -T ollama ollama pull "$MODEL"

log "Prewarming the adviser model"
python3 - <<'PY'
import json
import urllib.request

payload = json.dumps({
    'model': 'qwen3:4b-instruct-2507-q4_K_M',
    'prompt': 'Return a compact JSON object with key status and value ready.',
    'stream': False,
    'think': False,
    'format': {
        'type': 'object',
        'properties': {'status': {'type': 'string'}},
        'required': ['status'],
        'additionalProperties': False,
    },
    'keep_alive': '30m',
    'options': {
        'temperature': 0.0,
        'num_ctx': 2048,
        'num_predict': 32,
    },
}).encode('utf-8')
request = urllib.request.Request(
    'http://localhost:11434/api/generate',
    data=payload,
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(request, timeout=180) as response:
    body = json.loads(response.read().decode('utf-8'))
if not body.get('done'):
    raise SystemExit('Ollama prewarm did not complete.')
print('prewarm=ok')
print('model=' + str(body.get('model')))
print('output_tokens=' + str(body.get('eval_count')))
PY

log "Recreating Django and Celery with the faster adviser settings"
"${COMPOSE[@]}" up -d --force-recreate backend worker beat

log "Waiting for Django"
for attempt in $(seq 1 180); do
  if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 180 ]]; then
    "${COMPOSE[@]}" logs --tail=300 backend worker ollama
    fail "Django did not become healthy."
  fi
  sleep 2
done

log "Checking AI readiness"
curl --fail --silent http://localhost:8000/api/v1/ai-readiness/ | python3 -m json.tool

log "Confirming active adviser settings"
"${COMPOSE[@]}" exec -T backend python manage.py shell <<'PY'
from django.conf import settings
print('advisor_model=' + settings.STARTUP_ADVISOR_LLM_MODEL)
print('timeout_seconds=' + str(settings.STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS))
print('context_length=' + str(settings.OLLAMA_CONTEXT_LENGTH))
print('max_output_tokens=' + str(settings.STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS))
print('rag_top_k=' + str(settings.STARTUP_ADVISOR_RAG_TOP_K))
print('rag_max_total_chars=' + str(settings.STARTUP_ADVISOR_RAG_MAX_TOTAL_CHARS))
PY

printf '\nFounder Adviser timeout repair complete.\n'
printf '1. Open http://localhost:5173/advisor\n'
printf '2. Hard refresh once with Ctrl+Shift+R\n'
printf '3. Click Generate briefing again\n'
printf '4. Watch: docker compose logs -f --tail=200 worker ollama backend\n'
printf '\nPrevious environment backup: .env.before-advisor-timeout-fix-%s\n' "$STAMP"
