from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import EligibilityAssessment
from apps.schemes.models import (
    Authority,
    EligibilityRule,
    Scheme,
    SchemeVersion,
)
from apps.sources.models import Source, SourceDocument
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db


def make_user(
    *,
    username: str,
    is_staff: bool = False,
):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        is_staff=is_staff,
    )


def make_profile(*, owner, name: str):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.MVP,
        incorporation_date=date(2025, 1, 15),
        dpiit_recognized=True,
        profile_data={},
    )


def make_scheme(
    *,
    key: str,
    with_current_version: bool = True,
) -> Scheme:
    authority = Authority.objects.create(
        name=f"Authority {key}",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Scheme {key}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )

    if not with_current_version:
        return scheme

    source = Source.objects.create(
        name=f"Source {key}",
        official_domain=f"{key}.example.gov.in",
        listing_url=f"https://{key}.example.gov.in",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://{key}.example.gov.in/source",
        content_hash=f"{key}-hash",
        retrieved_at=timezone.now(),
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"{key}-version-hash",
        official_url=f"https://{key}.example.gov.in/scheme",
        verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
    )
    EligibilityRule.objects.create(
        scheme_version=version,
        field_path="dpiit_recognized",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        rule_group="all",
        evidence_text="DPIIT recognition is required.",
        manually_verified=True,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version", "updated_at"])
    return scheme


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_profile_owner_can_create_persisted_assessment():
    owner = make_user(username="api-owner")
    profile = make_profile(owner=owner, name="Owner Startup")
    scheme = make_scheme(key="api-owner")
    client = authenticated_client(owner)

    response = client.post(
        reverse("eligibility-evaluate"),
        {
            "scheme_id": str(scheme.id),
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-20",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["scheme_id"] == str(scheme.id)
    assert response.data["scheme_version_id"] == str(scheme.current_version_id)
    assert response.data["result"] == "eligible"
    assert response.data["engine_version"] == "rules-v5"
    assert response.data["assessment_date"] == "2026-07-20"
    assert response.data["profile_snapshot"]["id"] == str(profile.id)
    assert EligibilityAssessment.objects.count() == 1


def test_staff_can_assess_another_users_profile():
    owner = make_user(username="staff-target-owner")
    staff = make_user(
        username="assessment-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Staff Target Startup",
    )
    scheme = make_scheme(key="staff-target")
    client = authenticated_client(staff)

    response = client.post(
        reverse("eligibility-evaluate"),
        {
            "scheme_id": str(scheme.id),
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assessment = EligibilityAssessment.objects.get()
    assert assessment.requested_by == staff
    assert assessment.startup_profile == profile


def test_other_user_receives_404_for_unowned_profile():
    owner = make_user(username="private-profile-owner")
    other = make_user(username="private-profile-other")
    profile = make_profile(
        owner=owner,
        name="Private Startup",
    )
    scheme = make_scheme(key="private-profile")
    client = authenticated_client(other)

    response = client.post(
        reverse("eligibility-evaluate"),
        {
            "scheme_id": str(scheme.id),
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert EligibilityAssessment.objects.count() == 0


def test_scheme_without_current_version_returns_409():
    owner = make_user(username="no-version-owner")
    profile = make_profile(
        owner=owner,
        name="No Version Startup",
    )
    scheme = make_scheme(
        key="no-version",
        with_current_version=False,
    )
    client = authenticated_client(owner)

    response = client.post(
        reverse("eligibility-evaluate"),
        {
            "scheme_id": str(scheme.id),
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert EligibilityAssessment.objects.count() == 0


def test_legacy_raw_profile_payload_is_rejected():
    owner = make_user(username="legacy-profile-owner")
    profile = make_profile(
        owner=owner,
        name="Legacy Payload Startup",
    )
    scheme = make_scheme(key="legacy-profile")
    client = authenticated_client(owner)

    response = client.post(
        reverse("eligibility-evaluate"),
        {
            "scheme_id": str(scheme.id),
            "startup_profile_id": str(profile.id),
            "profile": {
                "dpiit_recognized": False,
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "profile" in response.data
    assert EligibilityAssessment.objects.count() == 0
