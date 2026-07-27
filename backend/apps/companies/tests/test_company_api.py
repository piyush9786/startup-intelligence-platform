import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Company

pytestmark = pytest.mark.django_db


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
    )
    Company.objects.create(
        canonical_name="Excluded Commerce",
        industry="E-commerce",
        business_model="marketplace",
        country="India",
        operating_status=Company.OperatingStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("company-list"), {"industry": "B2B SaaS"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(included.id)


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
