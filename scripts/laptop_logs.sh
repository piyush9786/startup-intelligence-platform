#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laptop_common.sh"
compose logs -f --tail=200 backend worker frontend ollama
