import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.schemes.models import Authority, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


def make_scheme(name, *, lifecycle_status, verification_status):
    slug = name.casefold().replace(" ", "-")
    source = Source.objects.create(
        name=f"{name} source",
        official_domain=f"{slug}.example.gov.in",
        listing_url="https://example.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://{slug}.example.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash=f"{name}-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(name=f"{name} authority")
    scheme = Scheme.objects.create(
        canonical_name=name,
        authority=authority,
        lifecycle_status=lifecycle_status,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"{name}-version",
        official_url="https://example.gov.in/scheme/",
        verification_status=verification_status,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version"])
    return scheme


def test_public_catalog_only_exposes_active_verified_schemes():
    visible = make_scheme(
        "Public verified scheme",
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    make_scheme(
        "Draft scheme",
        lifecycle_status=Scheme.LifecycleStatus.DRAFT,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    make_scheme(
        "Rejected scheme",
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        verification_status=SchemeVersion.VerificationStatus.REJECTED,
    )

    response = APIClient().get(reverse("scheme-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.id)


def test_staff_catalog_can_review_non_public_schemes():
    make_scheme(
        "Internal draft scheme",
        lifecycle_status=Scheme.LifecycleStatus.DRAFT,
        verification_status=SchemeVersion.VerificationStatus.REVIEW_REQUIRED,
    )
    staff = User.objects.create_user(
        username="scheme-admin",
        email="scheme-admin@example.com",
        password="test-password",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=staff)

    response = client.get(reverse("scheme-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
