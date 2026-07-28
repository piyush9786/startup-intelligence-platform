#!/usr/bin/env bash
set -Eeuo pipefail
USE_GPU=false
case "${1:-}" in
  --gpu) USE_GPU=true ;;
  "") ;;
  *) echo "Usage: $0 [--gpu]" >&2; exit 2 ;;
esac
export USE_GPU
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laptop_common.sh"
require_command docker
prepare_env
compose up -d
compose ps
