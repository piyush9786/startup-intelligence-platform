#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

GOLD="training/startupintel_slm/data_gold"
CURRENT="training/startupintel_slm/data"
OUT="training/startupintel_slm/data_compact"

if [[ ! -d "$GOLD" ]]; then
  echo "data_gold not found; preserving current export as gold."
  cp -a "$CURRENT" "$GOLD"
fi

rm -rf "$OUT"

python3 training/startupintel_slm/build_compact_dataset.py \
  --gold-dir "$GOLD" \
  --output-dir "$OUT" \
  --synthetic-advisor 500 \
  --synthetic-research 500

python3 training/startupintel_slm/validate_compact_dataset.py \
  --data-dir "$OUT"

echo
echo "===================================================="
echo " COMPACT DATASET READY"
echo "===================================================="
cat "$OUT/manifest.json"
echo
wc -l \
  "$OUT/train.jsonl" \
  "$OUT/validation.jsonl" \
  "$OUT/test.jsonl"
