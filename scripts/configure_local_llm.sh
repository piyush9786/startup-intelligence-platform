#!/usr/bin/env bash
set -Eeuo pipefail

PROFILE="balanced"
RAG_ENABLED="true"

usage() {
  cat <<'EOF'
Usage: ./scripts/configure_local_llm.sh [--balanced|--fast] [--no-rag]

  --balanced  qwen3:8b-q4_K_M, 8K context, 12 CPU / 12 GB Ollama limit (default)
  --fast      qwen3:4b-instruct-2507-q4_K_M, 6K context, 10 CPU / 8 GB limit
  --no-rag    Do not enable Qdrant/document embedding retrieval
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --balanced) PROFILE="balanced" ;;
    --fast) PROFILE="fast" ;;
    --no-rag) RAG_ENABLED="false" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\n\033[1;33mWARNING: %s\033[0m\n' "$*" >&2; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

for command in docker curl python3; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required."
done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
[[ -f docker-compose.yml ]] || fail "Run this command from the project directory."
[[ -f docker-compose.llm.yml ]] || fail "docker-compose.llm.yml is missing. Re-extract the hotfix."

if [[ ! -f .env ]]; then
  [[ -f .env.example ]] || fail ".env and .env.example are both missing."
  cp .env.example .env
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
cp .env ".env.before-llm-${TIMESTAMP}"

if [[ "$PROFILE" == "balanced" ]]; then
  MODEL="qwen3:8b-q4_K_M"
  CONTEXT="8192"
  CPU_LIMIT="12.0"
  MEMORY_LIMIT="12g"
  MEMORY_RESERVATION="8g"
  ADVISOR_TIMEOUT="600"
else
  MODEL="qwen3:4b-instruct-2507-q4_K_M"
  CONTEXT="6144"
  CPU_LIMIT="10.0"
  MEMORY_LIMIT="8g"
  MEMORY_RESERVATION="5g"
  ADVISOR_TIMEOUT="420"
fi

EMBEDDING_MODEL="embeddinggemma"

log "Writing the ${PROFILE} CPU-first LLM profile"
python3 - "$MODEL" "$CONTEXT" "$CPU_LIMIT" "$MEMORY_LIMIT" "$MEMORY_RESERVATION" "$ADVISOR_TIMEOUT" "$RAG_ENABLED" "$EMBEDDING_MODEL" <<'PY'
from pathlib import Path
import sys

(
    model,
    context,
    cpu_limit,
    memory_limit,
    memory_reservation,
    advisor_timeout,
    rag_enabled,
    embedding_model,
) = sys.argv[1:]

values = {
    "COMPOSE_FILE": "docker-compose.yml:docker-compose.llm.yml",
    "STARTUP_ADVISOR_LLM_PROVIDER": "ollama",
    "OLLAMA_BASE_URL": "http://ollama:11434",
    "STARTUP_ADVISOR_LLM_MODEL": model,
    "CHATBOT_LLM_MODEL": model,
    "OLLAMA_CONTEXT_LENGTH": context,
    "OLLAMA_NUM_PARALLEL": "1",
    "OLLAMA_MAX_LOADED_MODELS": "2" if rag_enabled == "true" else "1",
    "OLLAMA_MAX_QUEUE": "32",
    "OLLAMA_FLASH_ATTENTION": "1",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_CPU_LIMIT": cpu_limit,
    "OLLAMA_MEMORY_LIMIT": memory_limit,
    "OLLAMA_MEMORY_RESERVATION": memory_reservation,
    "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS": advisor_timeout,
    "STARTUP_ADVISOR_LLM_TEMPERATURE": "0.30",
    "STARTUP_ADVISOR_LLM_SEED": "7",
    "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS": "1536",
    "STARTUP_ADVISOR_LLM_KEEP_ALIVE": "20m",
    "STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS": "1200",
    "STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS": "1500",
    "CHATBOT_LLM_ENABLED": "true",
    "CHATBOT_LLM_TIMEOUT_SECONDS": "240",
    "CHATBOT_LLM_MAX_OUTPUT_TOKENS": "512",
    "CHATBOT_LLM_HISTORY_TURNS": "4",
    "CHATBOT_LLM_KEEP_ALIVE": "20m",
    "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED": "true",
    "STARTUP_ADVISOR_RAG_ENABLED": rag_enabled,
    "RESEARCH_VECTOR_RAG_ENABLED": rag_enabled,
    "STARTUP_ADVISOR_EMBEDDING_MODEL": embedding_model,
    "STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS": "90",
    "STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE": "8",
    "STARTUP_ADVISOR_EMBEDDING_KEEP_ALIVE": "20m",
    "STARTUP_ADVISOR_RAG_TOP_K": "4",
    "STARTUP_ADVISOR_RAG_MAX_PROMPT_DOCUMENTS": "4",
    "STARTUP_ADVISOR_RAG_MAX_CHARS_PER_CHUNK": "900",
    "STARTUP_ADVISOR_RAG_MAX_TOTAL_CHARS": "3600",
    "RESEARCH_VECTOR_RAG_TOP_K": "6",
    "CELERY_WORKER_CONCURRENCY": "1",
}


def update(path: Path) -> None:
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line and not line.lstrip().startswith("#") else None
        if key in values:
            if key not in seen:
                result.append(f"{key}={values[key]}")
                seen.add(key)
        else:
            result.append(line)
    if result and result[-1] != "":
        result.append("")
    for key, value in values.items():
        if key not in seen:
            result.append(f"{key}={value}")
    path.write_text("\n".join(result).rstrip() + "\n", encoding="utf-8")


update(Path(".env"))
update(Path(".env.example"))
PY

# Existing helper scripts explicitly pass docker-compose.yml, so teach them to
# include the LLM override when it is present. This edit is idempotent.
python3 <<'PY'
from pathlib import Path

path = Path("scripts/laptop_common.sh")
if path.exists():
    text = path.read_text(encoding="utf-8")
    if "docker-compose.llm.yml" not in text:
        needle = "  printf '%s\\n' -f docker-compose.yml\n"
        insertion = (
            needle
            + "  if [[ -f docker-compose.llm.yml ]]; then\n"
            + "    printf '%s\\n' -f docker-compose.llm.yml\n"
            + "  fi\n"
        )
        if needle in text:
            text = text.replace(needle, insertion, 1)
            path.write_text(text, encoding="utf-8")
        else:
            print("WARNING: could not patch scripts/laptop_common.sh automatically")
PY

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.llm.yml)
"${COMPOSE[@]}" config --quiet

log "Recreating Ollama with CPU and memory limits"
"${COMPOSE[@]}" up -d --force-recreate ollama

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

log "Pulling generation model: ${MODEL}"
"${COMPOSE[@]}" exec -T ollama ollama pull "$MODEL"

if [[ "$RAG_ENABLED" == "true" ]]; then
  log "Pulling embedding model: ${EMBEDDING_MODEL}"
  "${COMPOSE[@]}" exec -T ollama ollama pull "$EMBEDDING_MODEL"
fi

log "Recreating Django and Celery with the new LLM settings"
"${COMPOSE[@]}" up -d --force-recreate backend worker beat

log "Waiting for Django"
for attempt in $(seq 1 180); do
  if curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 180 ]]; then
    "${COMPOSE[@]}" logs --tail=300 backend
    fail "Django did not become healthy after the LLM configuration change."
  fi
  sleep 2
done

log "Running the integrated LLM doctor"
if ! "${COMPOSE[@]}" exec -T backend python manage.py llm_doctor; then
  "${COMPOSE[@]}" logs --tail=250 ollama backend worker
  fail "The LLM doctor failed. Review the logs above."
fi

log "AI readiness"
curl --fail --silent http://localhost:8000/api/v1/ai-readiness/ | python3 -m json.tool

printf '\nLocal LLM configuration complete.\n'
printf '  Profile:  %s\n' "$PROFILE"
printf '  Model:    %s\n' "$MODEL"
printf '  Context:  %s tokens\n' "$CONTEXT"
printf '  RAG:      %s\n' "$RAG_ENABLED"
printf '  Advisor:  http://localhost:5173\n'
printf '  Status:   ./scripts/llm_status.sh\n'
printf '\nYour previous .env is saved as .env.before-llm-%s\n' "$TIMESTAMP"
