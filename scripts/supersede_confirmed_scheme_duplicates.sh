#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Previewing exact duplicate supersession"
docker compose exec -T backend \
  python manage.py supersede_known_duplicate_schemes --dry-run --expected-total 75

echo
echo "==> Superseding duplicate rows without deleting their versions or evidence"
docker compose exec -T backend \
  python manage.py supersede_known_duplicate_schemes --expected-total 75

echo
echo "==> Rebuilding TF-IDF from the 75 active verified unique schemes"
docker compose exec -T backend \
  python manage.py train_ml_models --real --model tfidf

echo
echo "==> Validating deduplicated catalog and search index"
docker compose exec -T backend python manage.py shell <<'PY'
import joblib
from apps.ml_engine.models import MLModelRegistry
from apps.schemes.models import Scheme, SchemeVersion

active = Scheme.objects.filter(
    lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
)
entry = MLModelRegistry.objects.filter(model_type="tfidf", status="active").order_by("-model_version").first()
if entry is None:
    raise SystemExit("No active TF-IDF registry entry exists.")
artifact = joblib.load(entry.artifact_path)
print("active_verified_unique=", active.count(), sep="")
print("tfidf_version=", entry.model_version, sep="")
print("tfidf_stage=", entry.deployment_stage, sep="")
print("tfidf_indexed=", len(artifact["scheme_version_ids"]), sep="")
assert active.count() == 75
assert len(artifact["scheme_version_ids"]) == 75
print("Duplicate supersession validation: PASS")
PY

echo
echo "Complete: duplicate audit rows were retained, while active catalog/search now uses 75 unique schemes."
