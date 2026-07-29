#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

log() {
  printf '\n\033[1;34m==> %s\033[0m\n' "$*"
}

warn() {
  printf '\n\033[1;33mWARNING: %s\033[0m\n' "$*" >&2
}

fail() {
  printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required."
}

replace_env_value() {
  local key="$1"
  local value="$2"
  python3 - "$key" "$value" <<'PY'
from pathlib import Path
import sys

key, value = sys.argv[1], sys.argv[2]
path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines()
updated = []
found = False
for line in lines:
    if line.startswith(f'{key}='):
        updated.append(f'{key}={value}')
        found = True
    else:
        updated.append(line)
if not found:
    updated.append(f'{key}={value}')
path.write_text('\n'.join(updated) + '\n', encoding='utf-8')
PY
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
  fi
}

prepare_env() {
  require_command python3
  if [[ ! -f .env ]]; then
    cp .env.example .env
  fi

  local key
  for key in DJANGO_SECRET_KEY POSTGRES_PASSWORD NEO4J_PASSWORD MINIO_SECRET_KEY; do
    local current
    current="$(grep -E "^${key}=" .env | head -1 | cut -d= -f2- || true)"
    case "${current,,}" in
      ""|change-me|changeme|password|startup|unsafe-development-key)
        replace_env_value "${key}" "$(random_secret)"
        ;;
    esac
  done

  replace_env_value LOCAL_UID "$(id -u)"
  replace_env_value LOCAL_GID "$(id -g)"
}

compose_args() {
  printf '%s\n' -f docker-compose.yml
  if [[ -f docker-compose.llm.yml ]]; then
    printf '%s\n' -f docker-compose.llm.yml
  fi
  if [[ "${USE_GPU:-false}" == "true" ]]; then
    printf '%s\n' -f docker-compose.gpu.yml
  fi
}

compose() {
  local args=()
  while IFS= read -r item; do
    args+=("${item}")
  done < <(compose_args)
  docker compose "${args[@]}" "$@"
}
