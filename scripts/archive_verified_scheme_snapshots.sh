#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Starting Django, PostgreSQL, MinIO, Redis, and Ollama"
docker compose up -d postgres redis minio minio_init ollama ollama_init backend

echo
echo "==> Previewing official-source snapshot archival"
docker compose exec -T backend \
  python manage.py archive_verified_scheme_sources --dry-run

echo
echo "==> Archiving raw HTML/PDF evidence in MinIO"
docker compose exec -T backend \
  python manage.py archive_verified_scheme_sources

echo
echo "==> Evidence snapshot audit"
docker compose exec -T backend python manage.py shell <<'PY'
from django.db.models import F
from apps.schemes.models import Scheme, SchemeVersion

verified = SchemeVersion.objects.filter(
    verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    scheme__lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    scheme__current_version_id=F("id"),
)
missing = verified.filter(source_document__storage_key="")
print("verified_active_schemes=", verified.count(), sep="")
print("with_stored_snapshot=", verified.exclude(source_document__storage_key="").count(), sep="")
print("missing_stored_snapshot=", missing.count(), sep="")
if missing.exists():
    print("Sources still missing snapshots:")
    for url in missing.values_list("source_document__source_url", flat=True).distinct():
        print("-", url)
PY

echo
echo "Snapshot archival finished. Sources blocked by robots.txt or remote errors remain listed for review."
