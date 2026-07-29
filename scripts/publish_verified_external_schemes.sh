#!/usr/bin/env bash
set -euo pipefail

EXPECTED_TOTAL="${EXPECTED_VERIFIED_SCHEMES:-77}"

if [[ ! -f docker-compose.yml || ! -d backend ]]; then
  echo "Run this script from the startup-intelligence-platform project root." >&2
  exit 1
fi

step() { printf '\n==> %s\n' "$1"; }

step "Checking the Django backend"
docker compose up -d backend
until curl --fail --silent http://localhost:8000/api/v1/health/ >/dev/null; do
  sleep 2
done

step "Previewing reviewer-verified external scheme publication"
docker compose exec -T backend \
  python manage.py canonicalize_verified_external_schemes \
  --dry-run \
  --expected-total "$EXPECTED_TOTAL"

step "Publishing verified external schemes into the canonical catalog"
docker compose exec -T backend \
  python manage.py canonicalize_verified_external_schemes \
  --expected-total "$EXPECTED_TOTAL"

step "Rebuilding TF-IDF from the full current verified canonical catalog"
docker compose exec -T backend \
  python manage.py train_ml_models --real --model tfidf

step "Validating canonical counts, evidence links, and TF-IDF IDs"
docker compose exec -T -e EXPECTED_VERIFIED_SCHEMES="$EXPECTED_TOTAL" backend python manage.py shell <<'PY'
import joblib

from apps.knowledge.models import ExternalSchemeRecord
from apps.ml_engine.models import MLModelRegistry
from apps.schemes.models import Scheme, SchemeVersion
from apps.sources.models import SourceDocument

verified = Scheme.objects.filter(
    lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
)
unmatched = ExternalSchemeRecord.objects.filter(
    dataset__is_active=True,
    review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
    matched_scheme__isnull=True,
)
proof_records = SourceDocument.objects.filter(
    extractor_version="external-review-canonicalizer-v1",
    status=SourceDocument.Status.VERIFIED,
)
entry = (
    MLModelRegistry.objects.filter(model_type="tfidf", status="active")
    .order_by("-model_version")
    .first()
)
if entry is None:
    raise RuntimeError("No active TF-IDF registry entry was created.")
artifact = joblib.load(entry.artifact_path)
artifact_ids = {str(value) for value in artifact["scheme_version_ids"]}
database_ids = {
    str(value)
    for value in verified.values_list("current_version_id", flat=True)
    if value
}

print("canonical_verified=", verified.count(), sep="")
print("verified_external_unmatched=", unmatched.count(), sep="")
print("proof_documents=", proof_records.count(), sep="")
print("tfidf_version=", entry.model_version, sep="")
print("tfidf_stage=", entry.deployment_stage, sep="")
print("tfidf_indexed=", len(artifact_ids), sep="")
print("tfidf_missing_current_ids=", len(database_ids - artifact_ids), sep="")
print("tfidf_stale_ids=", len(artifact_ids - database_ids), sep="")

expected = int(__import__("os").environ.get("EXPECTED_VERIFIED_SCHEMES", "77"))
assert verified.count() == expected, (verified.count(), expected)
assert unmatched.count() == 0
assert artifact_ids == database_ids
print("Verified scheme publication validation: PASS")
PY

step "Restarting application services so every process sees the new catalog"
docker compose restart backend worker beat frontend >/dev/null

echo
echo "Complete: ${EXPECTED_TOTAL} unique reviewer-verified schemes are canonical and searchable."
echo "Open http://localhost:5173/dashboard and hard refresh once with Ctrl+Shift+R."
