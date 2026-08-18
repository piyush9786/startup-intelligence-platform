#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

SLM_DIR="$ROOT/training/startupintel_slm"
PYTHON="$SLM_DIR/.venv-local/bin/python"

export STARTUPINTEL_SLM_HOST="${STARTUPINTEL_SLM_HOST:-0.0.0.0}"
export STARTUPINTEL_SLM_PORT="${STARTUPINTEL_SLM_PORT:-8091}"
export STARTUPINTEL_SLM_BASE_MODEL="${STARTUPINTEL_SLM_BASE_MODEL:-Qwen/Qwen3-0.6B}"
export STARTUPINTEL_SLM_ADAPTER="${STARTUPINTEL_SLM_ADAPTER:-$SLM_DIR/outputs/startup-intel-0.6b-selected}"
export STARTUPINTEL_SLM_MAX_NEW_TOKENS="${STARTUPINTEL_SLM_MAX_NEW_TOKENS:-768}"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

exec "$PYTHON" \
  "$SLM_DIR/serve_startupintel_nf4.py"
