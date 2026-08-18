#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

MODEL="${1:-startup-intel:1.7b}"
ENV_FILE=".env"
STAMP="$(date +%Y%m%d-%H%M%S)"

cp "$ENV_FILE" \
   "$ENV_FILE.before-custom-slm-$STAMP"

python3 - "$MODEL" <<'PY'
from pathlib import Path
import sys

model = sys.argv[1]
path = Path(".env")
updates = {
    "STARTUP_ADVISOR_LLM_MODEL": model,
    "CHATBOT_LLM_MODEL": model,
    "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS": "1200",
    "STARTUP_ADVISOR_LLM_TEMPERATURE": "0.15",
    "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS": "240",
    "OLLAMA_CONTEXT_LENGTH": "4096",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
out = []
for line in lines:
    if "=" not in line or line.lstrip().startswith("#"):
        out.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in updates:
        if key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
    else:
        out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

echo "Using model: $MODEL"
ollama show "$MODEL" >/dev/null

docker compose up -d --force-recreate \
  backend worker beat

echo
echo "Custom SLM activated."
echo "Founder Advisor and the current Research generator "
echo "will use the same configured provider model."
