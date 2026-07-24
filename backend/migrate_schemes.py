import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.knowledge.models import ExternalSchemeRecord
from apps.schemes.models import Scheme, SchemeVersion, Authority
from django.utils import timezone

def run_migration():
    records = ExternalSchemeRecord.objects.filter(review_status='verified', matched_scheme__isnull=True)
    print(f"Found {records.count()} verified external records to migrate")

    authority, _ = Authority.objects.get_or_create(
        name="External Sources",
        defaults={
            "authority_type": "state_government",
            "department": "External Database",
            "name": "External Sources"
        }
    )

    # Need a dummy source document for SchemeVersion
    from apps.sources.models import SourceDocument, Source
    source, _ = Source.objects.get_or_create(
        name="External Database Import",
        defaults={
            "official_domain": "example.com",
            "listing_url": "https://example.com/schemes",
            "authority_tier": "E"
        }
    )
    source_doc, _ = SourceDocument.objects.get_or_create(
        source=source,
        source_url="https://example.com/import",
        defaults={"status": "approved", "content_hash": "dummy_hash", "mime_type": "text/plain", "title": "External Import", "retrieved_at": timezone.now()}
    )

    created = 0
    for r in records:
        scheme, is_new = Scheme.objects.get_or_create(
            canonical_name=r.scheme_name,
            defaults={
                "authority": authority,
                "lifecycle_status": Scheme.LifecycleStatus.ACTIVE,
                "short_name": r.normalized_name[:150]
            }
        )
        if is_new:
            sv = SchemeVersion.objects.create(
                scheme=scheme,
                version_number=1,
                source_document=source_doc,
                description=r.eligibility or "Details available from external source",
                categories=[r.sector] if r.sector else [],
                support_types=[r.funding_type] if r.funding_type else ["grant"],
                verification_status=SchemeVersion.VerificationStatus.VERIFIED,
                valid_from=timezone.now().date(),
                captured_at=timezone.now(),
                content_hash=f"ext_{r.id}",
                official_url=r.official_application_url or "https://example.com"
            )
            scheme.current_version = sv
            scheme.save()
            
            # Link back
            r.matched_scheme = scheme
            r.save(update_fields=['matched_scheme'])
            created += 1

    print(f"Created {created} new canonical schemes!")

if __name__ == "__main__":
    run_migration()
