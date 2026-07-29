#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${1:-/home/ps/Pictures/startup-intelligence-platform-main}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
REPORT="${PROJECT_DIR}/legacy-assets-${TIMESTAMP}.txt"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Legacy project directory not found: $SOURCE_DIR" >&2
  exit 1
fi

{
  echo "LEGACY STARTUP INTELLIGENCE ASSET INVENTORY"
  echo "Generated: $(date --iso-8601=seconds)"
  echo "Source: $SOURCE_DIR"
  echo "Current project: $PROJECT_DIR"
  echo
  echo "== TOP-LEVEL CONTENT =="
  find "$SOURCE_DIR" -mindepth 1 -maxdepth 2 \
    -not -path '*/.git/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/.venv/*' \
    -printf '%y %10s %TY-%Tm-%Td %TH:%TM %p\n' | sort
  echo
  echo "== MODEL / TRAINING ARTIFACTS =="
  find "$SOURCE_DIR" -type f \
    \( -iname '*.pt' -o -iname '*.pth' -o -iname '*.bin' -o -iname '*.safetensors' \
       -o -iname '*.onnx' -o -iname '*.joblib' -o -iname '*.pkl' -o -iname '*.pickle' \
       -o -iname '*.h5' -o -iname '*.keras' -o -iname '*.gguf' -o -iname '*.npy' \
       -o -iname '*.npz' -o -iname '*.faiss' -o -iname '*.index' \) \
    -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort -nr
  echo
  echo "== DATASETS / CRAWL OUTPUTS =="
  find "$SOURCE_DIR" -type f \
    \( -iname '*.csv' -o -iname '*.json' -o -iname '*.jsonl' -o -iname '*.parquet' \
       -o -iname '*.ndjson' -o -iname '*.xml' -o -iname '*.html' -o -iname '*.sqlite' \
       -o -iname '*.sqlite3' -o -iname '*.db' \) \
    -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -not -path '*/package-lock.json' \
    -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort -nr
  echo
  echo "== CRAWLER / SCRAPER CODE AND CONFIG =="
  find "$SOURCE_DIR" -type f \
    \( -iname '*crawl*' -o -iname '*crawler*' -o -iname '*scrape*' -o -iname '*scraper*' \
       -o -iname '*spider*' -o -iname '*harvest*' -o -iname '*source*' \) \
    -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort
  echo
  echo "== TRAINING CODE AND CONFIG =="
  find "$SOURCE_DIR" -type f \
    \( -iname '*train*' -o -iname '*fine*tun*' -o -iname '*embedding*' -o -iname '*vector*' \
       -o -iname '*rag*' -o -iname '*evaluate*' -o -iname '*dataset*' \) \
    -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort
  echo
  echo "== LARGE FILES (>= 10 MiB) =="
  find "$SOURCE_DIR" -type f -size +10M \
    -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort -nr
} > "$REPORT"

printf 'Legacy asset inventory written to:\n%s\n' "$REPORT"
printf 'Upload this report before merging old training/crawl assets into live code.\n'
