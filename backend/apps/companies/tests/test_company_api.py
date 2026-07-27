import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import (
    Company,
    CompanyDataSource,
    CompanySourceRecord,
    RawCompanyDataset,
)

pytestmark = pytest.mark.django_db


def attach_reviewed_provenance(company):
    suffix = str(company.id)
    source = CompanyDataSource.objects.create(
        slug=f"reviewed-{suffix}",
        name=f"Reviewed source {suffix}",
        source_type=CompanyDataSource.SourceType.PUBLIC_DATASET,
        reliability_score="0.800",
        verification_status=CompanyDataSource.VerificationStatus.REVIEWED,
    )
    dataset = RawCompanyDataset.objects.create(
        dataset_id=f"dataset-{suffix}",
        source=source,
        original_filename="companies.csv",
        checksum_sha256=suffix.replace("-", "").ljust(64, "0"),
        retrieved_at=timezone.now(),
    )
    CompanySourceRecord.objects.create(
        company=company,
        source=source,
        latest_dataset=dataset,
        external_id=f"company-{suffix}",
        confidence_score="0.800",
    )


def test_company_catalog_requires_authentication():
    response = APIClient().get(reverse("company-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_founder_can_filter_company_catalog():
    user = User.objects.create_user(
        username="company-reader",
        email="company-reader@example.com",
        password="test-password",
    )
    included = Company.objects.create(
        canonical_name="Included SaaS",
        industry="B2B SaaS",
        business_model="subscription",
        country="India",
        operating_status=Company.OperatingStatus.ACTIVE,
        verification_status=Company.VerificationStatus.VERIFIED,
    )
    Company.objects.create(
        canonical_name="Excluded Commerce",
        industry="E-commerce",
        business_model="marketplace",
        country="India",
        operating_status=Company.OperatingStatus.ACTIVE,
        verification_status=Company.VerificationStatus.VERIFIED,
    )
    attach_reviewed_provenance(included)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("company-list"), {"industry": "B2B SaaS"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(included.id)


def test_founder_cannot_read_unverified_or_disputed_companies():
    user = User.objects.create_user(
        username="verified-company-reader",
        email="verified-company-reader@example.com",
        password="test-password",
    )
    visible = Company.objects.create(
        canonical_name="Reviewed Company",
        industry="B2B SaaS",
        business_model="subscription",
        country="India",
        verification_status=Company.VerificationStatus.PARTIALLY_VERIFIED,
    )
    Company.objects.create(
        canonical_name="Unreviewed Company",
        industry="B2B SaaS",
        business_model="subscription",
        country="India",
        verification_status=Company.VerificationStatus.UNVERIFIED,
    )
    attach_reviewed_provenance(visible)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("company-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.id)


def test_company_source_registry_is_admin_only():
    founder = User.objects.create_user(
        username="company-founder",
        email="company-founder@example.com",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(user=founder)

    response = client.get(reverse("company-data-source-list"))

    assert response.status_code == status.HTTP_403_FORBIDDEN
