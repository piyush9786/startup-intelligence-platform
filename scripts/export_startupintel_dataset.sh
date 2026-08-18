#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

OUT_HOST="training/startupintel_slm/data"
OUT_CONTAINER="/tmp/startupintel_sft"

mkdir -p "$OUT_HOST"

docker compose exec -T backend \
  rm -rf "$OUT_CONTAINER"

docker compose exec -T backend \
  python manage.py export_startupintel_sft \
  --output-dir "$OUT_CONTAINER" \
  --include-partial-research

CID="$(docker compose ps -q backend)"
if [[ -z "$CID" ]]; then
  echo "Backend container not found." >&2
  exit 1
fi

rm -rf "$OUT_HOST"
mkdir -p "$OUT_HOST"

docker cp \
  "$CID:$OUT_CONTAINER/." \
  "$OUT_HOST/"

echo
echo "Dataset copied to:"
echo "$OUT_HOST"
echo
cat "$OUT_HOST/stats.json"
