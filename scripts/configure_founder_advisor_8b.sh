#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/ps/Project/startup-intelligence-platform}"
MODEL="${STARTUP_ADVISOR_8B_MODEL:-qwen3:8b-q4_K_M}"

cd "${PROJECT_DIR}"

for required in \
  .env \
  docker-compose.yml \
  backend/apps/startups/services/advisor_briefing.py \
  backend/apps/startups/services/llm_provider.py
do
  [[ -f "${required}" ]] || {
    echo "Missing required file: ${required}" >&2
    exit 1
  }
done

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=".hotfix-backups/founder-advisor-8b-${STAMP}"
mkdir -p "${BACKUP_DIR}/backend/apps/startups/services"
cp .env "${BACKUP_DIR}/.env"
cp backend/apps/startups/services/advisor_briefing.py \
  "${BACKUP_DIR}/backend/apps/startups/services/advisor_briefing.py"
cp backend/apps/startups/services/llm_provider.py \
  "${BACKUP_DIR}/backend/apps/startups/services/llm_provider.py"

echo "Backup created at ${BACKUP_DIR}"

python3 <<'PY'
from pathlib import Path

path = Path(".env")
lines = path.read_text(encoding="utf-8").splitlines()
updates = {
    "STARTUP_ADVISOR_LLM_PROVIDER": "ollama",
    "STARTUP_ADVISOR_LLM_MODEL": "qwen3:8b-q4_K_M",
    "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS": "1200",
    "STARTUP_ADVISOR_LLM_TEMPERATURE": "0.30",
    "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS": "512",
    "STARTUP_ADVISOR_LLM_KEEP_ALIVE": "15m",
    "OLLAMA_CONTEXT_LENGTH": "4096",
    "OLLAMA_NUM_PARALLEL": "1",
    "OLLAMA_MAX_LOADED_MODELS": "2",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_FLASH_ATTENTION": "1",
    "STARTUP_ADVISOR_RAG_ENABLED": "false",
    "STARTUP_ADVISOR_RAG_TOP_K": "1",
    "STARTUP_ADVISOR_RAG_MAX_TOTAL_CHARS": "700",
}

seen = set()
out = []
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        out.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in updates:
        if key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        continue
    out.append(line)

for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")

path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
print("Updated .env for the 8B compact profile.")
PY

python3 <<'PY'
from pathlib import Path

path = Path("backend/apps/startups/services/llm_provider.py")
text = path.read_text(encoding="utf-8")

if '"think": False' not in text and "'think': False" not in text:
    marker = '"stream": False,'
    if marker not in text:
        raise SystemExit("Ollama payload marker not found.")
    text = text.replace(
        marker,
        marker + '\n            "think": False,',
        1,
    )
    path.write_text(text, encoding="utf-8")
    print("Added think=False.")
else:
    print("think=False already present.")
PY

python3 <<'PY'
from pathlib import Path

path = Path("backend/apps/startups/services/advisor_briefing.py")
text = path.read_text(encoding="utf-8")

helper = r'''

_PROMPT_PROFILE_FIELDS = (
    "id", "startup_name", "legal_name", "description",
    "state", "district", "stage", "current_stage",
    "sectors", "sector", "technologies", "technology",
    "founder_category", "dpiit_recognized", "udyam_registered",
    "incorporation_date", "startup_age_months", "team_size",
    "monthly_revenue", "monthly_burn", "cash_balance",
    "funding_raised", "funding_required", "customer_segments",
    "traction",
)

_PROMPT_READINESS_FIELDS = (
    "id", "readiness_status", "overall_score", "score",
    "summary", "findings", "blocking_findings", "missing_fields",
    "answered_count", "unanswered_count",
)

_PROMPT_ACTION_PLAN_FIELDS = (
    "id", "readiness_status", "next_action", "actions",
    "blockers", "blocker_count", "total_action_count",
)

_PROMPT_RECOMMENDATION_FIELDS = (
    "id", "scheme_id", "scheme_version_id", "scheme_name",
    "canonical_name", "rank", "ranking_score", "score",
    "eligibility_result", "eligibility_score", "explanation",
    "reasons", "support_types", "verification_status",
    "official_url", "source_references",
)


def _compact_prompt_value(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        normalized = " ".join(value.split())
        return normalized[: (360 if depth < 3 else 220)]
    if isinstance(value, list):
        return [
            _compact_prompt_value(item, depth=depth + 1)
            for item in value[:5]
        ]
    if isinstance(value, dict):
        return {
            str(key): _compact_prompt_value(item, depth=depth + 1)
            for key, item in list(value.items())[:18]
        }
    return str(value)[:220]


def _select_prompt_fields(
    value: Any,
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        name: _compact_prompt_value(value[name])
        for name in field_names
        if name in value
    }


def _compact_startup_advisor_prompt_input(
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    # The complete immutable snapshot remains in source_input and is
    # rechecked after generation. Only the LLM prompt copy is reduced.
    compact: dict[str, Any] = {}

    for name in (
        "advisor_snapshot_id",
        "startup_profile_id",
        "snapshot_version",
        "created_at",
        "source_ids",
        "source_record_ids",
    ):
        if name in input_payload:
            compact[name] = _compact_prompt_value(input_payload[name])

    compact["profile"] = _select_prompt_fields(
        input_payload.get("profile"),
        _PROMPT_PROFILE_FIELDS,
    )
    compact["readiness"] = _select_prompt_fields(
        input_payload.get("readiness"),
        _PROMPT_READINESS_FIELDS,
    )
    compact["action_plan"] = _select_prompt_fields(
        input_payload.get("action_plan"),
        _PROMPT_ACTION_PLAN_FIELDS,
    )

    generation = input_payload.get("recommendation_generation")
    if isinstance(generation, dict):
        compact["recommendation_generation"] = _select_prompt_fields(
            generation,
            (
                "id", "status", "generated_at",
                "recommendation_count", "model_version",
            ),
        )

    recommendations = input_payload.get("recommendations")
    compact["recommendations"] = (
        [
            _select_prompt_fields(
                item,
                _PROMPT_RECOMMENDATION_FIELDS,
            )
            for item in recommendations[:5]
            if isinstance(item, dict)
        ]
        if isinstance(recommendations, list)
        else []
    )
    return compact
'''

if "_compact_startup_advisor_prompt_input" not in text:
    marker = "\ndef build_startup_advisor_briefing_prompt("
    if marker not in text:
        raise SystemExit("Prompt builder marker not found.")
    text = text.replace(marker, helper + marker, 1)

old = '"startup_advisor_snapshot": input_payload,'
new = (
    '"startup_advisor_snapshot": '
    '_compact_startup_advisor_prompt_input(input_payload),'
)
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("Prompt snapshot replacement marker not found.")

path.write_text(text, encoding="utf-8")
print("Installed compact prompt view.")
PY

python3 -m py_compile \
  backend/apps/startups/services/advisor_briefing.py \
  backend/apps/startups/services/llm_provider.py

echo "==> Starting Ollama"
docker compose up -d ollama

for _ in $(seq 1 90); do
  if docker compose exec -T ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> Pulling ${MODEL}"
docker compose exec -T ollama ollama pull "${MODEL}"

echo "==> Recreating backend, worker and beat"
docker compose up -d --force-recreate backend worker beat

for _ in $(seq 1 120); do
  if curl -fsS http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker compose exec -T backend python manage.py check

docker compose exec -T backend python manage.py shell <<'PY'
from django.conf import settings
from apps.startups.models import StartupAdvisorSnapshot
from apps.startups.services.advisor_briefing import (
    build_startup_advisor_briefing_prompt,
)

print("advisor_model=" + settings.STARTUP_ADVISOR_LLM_MODEL)
print("timeout_seconds=" + str(settings.STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS))
print("max_output_tokens=" + str(settings.STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS))
print("rag_enabled=" + str(settings.STARTUP_ADVISOR_RAG_ENABLED))

snapshot = StartupAdvisorSnapshot.objects.order_by("-created_at").first()
if snapshot is None:
    print("prompt_check=no_snapshot")
else:
    prompt = build_startup_advisor_briefing_prompt(
        source_snapshot=snapshot,
    )
    chars = sum(
        len(str(message.get("content") or ""))
        for message in prompt["messages"]
    )
    rough_tokens = max(1, chars // 4)
    print("prompt_chars=" + str(chars))
    print("rough_prompt_tokens=" + str(rough_tokens))
    if rough_tokens > 3300:
        raise SystemExit("Compact prompt is still too large.")
PY

echo "==> Prewarming 8B"
docker compose exec -T backend python manage.py shell <<'PY'
from django.conf import settings
import httpx

response = httpx.post(
    f"{settings.OLLAMA_BASE_URL}/api/chat",
    json={
        "model": settings.STARTUP_ADVISOR_LLM_MODEL,
        "messages": [
            {"role": "user", "content": "Reply with READY only."}
        ],
        "stream": False,
        "think": False,
        "keep_alive": "15m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 8,
        },
    },
    timeout=600,
)
response.raise_for_status()
payload = response.json()
print("prewarm=ok")
print("model=" + str(payload.get("model")))
print("reply=" + str(payload.get("message", {}).get("content", "")).strip())
PY

echo "Founder Adviser 8B compact profile is ready."
echo "Open http://localhost:5173/advisor and hard refresh once."
echo "Backup: ${BACKUP_DIR}"
