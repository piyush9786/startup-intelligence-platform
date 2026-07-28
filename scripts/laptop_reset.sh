#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laptop_common.sh"
if [[ "${1:-}" != "--yes" ]]; then
  fail "This deletes all local database and service volumes. Re-run with --yes."
fi
compose down -v --remove-orphans
rm -f .env
log "Local containers, volumes, and generated .env were removed"
