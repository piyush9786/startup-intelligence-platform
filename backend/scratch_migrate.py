import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.knowledge.models import ExternalSchemeRecord
from apps.schemes.models import Scheme, SchemeVersion, Authority
from django.utils import timezone
import uuid

records = ExternalSchemeRecord.objects.filter(review_status='verified', matched_scheme__isnull=True)
print(f"Found {records.count()} verified external records to migrate")

authority, _ = Authority.objects.get_or_create(
    canonical_name="External Sources",
    defaults={
        "authority_type": "state_government",
        "department": "External Database",
    }
)

created = 0
for r in records:
    scheme, is_new = Scheme.objects.get_or_create(
        canonical_name=r.scheme_name,
        defaults={
            "authority": authority,
            "status": "active"
        }
    )
    if is_new:
        SchemeVersion.objects.create(
            scheme=scheme,
            version_number=1,
            description=r.eligibility or "Details available from external source",
            categories=[r.sector] if r.sector else [],
            support_types=[r.funding_type] if r.funding_type else ["grant"],
            is_active=True,
            verification_status="verified",
            valid_from=timezone.now().date()
        )
        created += 1

print(f"Created {created} new canonical schemes!")
