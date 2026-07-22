from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import (
    IntegrityError,
    close_old_connections,
    connections,
    transaction,
)
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.services.assessment_drafts import (
    get_or_create_startup_assessment_draft,
)

pytestmark = pytest.mark.django_db


def make_user(*, username: str, is_staff: bool = False):
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
        legal_name=f"{name} Private Limited",
        description=(
            "A climate technology startup with a validated customer problem "
            "and an evidence-backed product proposition."
        ),
        incorporation_type="private_limited",
        incorporation_date=date(2025, 1, 15),
        state="Maharashtra",
        district="Pune",
        stage=StartupProfile.Stage.MVP,
        sectors=["climate_technology"],
        technologies=["software"],
        dpiit_recognized=True,
        udyam_registered=False,
        annual_turnover=Decimal("1000000.00"),
        revenue_stage="early_revenue",
        funding_required=Decimal("5000000.00"),
        funding_purpose="Product development and market expansion.",
        team_size=8,
        profile_data={"founder_role": "chief_executive_officer"},
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def valid_draft_data():
    return {
        "startup_name": "Assessment Workflow Startup",
        "legal_name": "Assessment Workflow Startup Private Limited",
        "description": (
            "A technology startup solving a clearly defined customer problem "
            "with a scalable digital product and early customer evidence."
        ),
        "incorporation_type": "private_limited",
        "incorporation_date": "2025-01-15",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "stage": "mvp",
        "sectors": ["software"],
        "technologies": ["artificial_intelligence"],
        "founder_categories": ["general"],
        "founder_gender": "woman",
        "dpiit_recognized": True,
        "udyam_registered": False,
        "annual_turnover": "1000000.00",
        "revenue_stage": "early_revenue",
        "funding_required": "5000000.00",
        "funding_purpose": "Product development and market expansion.",
        "team_size": 8,
        "founder_role": "chief_executive_officer",
        "founder_experience_years": 7,
        "number_of_founders": 2,
        "business_model": "business_to_business",
        "customer_status": "paying_customers",
        "preferred_funding_type": "grant",
        "skills_needs": ["sales"],
        "certification_needs": ["dpiit_recognition"],
        "compliance_support_needs": ["company_law"],
    }


def recommendation_generation(*, startup_profile, requested_by, assessment_date):
    del requested_by
    return SimpleNamespace(
        generation_id=uuid4(),
        ranking_version="recommendation-ranking-v1",
        startup_profile=startup_profile,
        assessment_date=assessment_date,
        assessments=[],
        recommendations=[],
        excluded_schemes=[],
    )


def test_owner_can_create_linked_prefilled_draft():
    owner = make_user(username="assessment-draft-owner")
    profile = make_profile(owner=owner, name="Prefilled Startup")

    response = authenticated_client(owner).post(
        reverse("startup-assessment-draft-list"),
        {
            "startup_profile_id": str(profile.id),
            "current_step": 3,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["current_step"] == 3
    assert response.data["data"]["startup_name"] == "Prefilled Startup"
    assert response.data["data"]["founder_role"] == "chief_executive_officer"
    assert response.data["completion_percent"] > 0


def test_draft_patch_merges_data_instead_of_replacing_it():
    owner = make_user(username="assessment-draft-merge")
    draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        current_step=1,
        data={
            "startup_name": "Merge Startup",
            "stage": "idea",
        },
    )

    response = authenticated_client(owner).patch(
        reverse(
            "startup-assessment-draft-detail",
            kwargs={"pk": draft.id},
        ),
        {
            "current_step": 2,
            "data": {
                "founder_role": "founder",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["current_step"] == 2
    assert response.data["data"]["startup_name"] == "Merge Startup"
    assert response.data["data"]["founder_role"] == "founder"


def test_user_cannot_link_another_users_profile():
    owner = make_user(username="assessment-private-owner")
    other = make_user(username="assessment-private-other")
    profile = make_profile(owner=owner, name="Private Startup")

    response = authenticated_client(other).post(
        reverse("startup-assessment-draft-list"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in response.data
    assert StartupAssessmentDraft.objects.count() == 0


def test_user_lists_only_visible_drafts():
    owner = make_user(username="assessment-list-owner")
    other = make_user(username="assessment-list-other")
    owner_draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        data={"startup_name": "Owner Draft"},
    )
    StartupAssessmentDraft.objects.create(
        owner=other,
        data={"startup_name": "Other Draft"},
    )

    response = authenticated_client(owner).get(
        reverse("startup-assessment-draft-list"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(owner_draft.id)


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_submit_creates_profile_and_downstream_records(mock_generate):
    owner = make_user(username="assessment-submit-owner")
    draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        current_step=8,
        data=valid_draft_data(),
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(owner).post(
        reverse(
            "startup-assessment-draft-submit",
            kwargs={"draft_id": draft.id},
        ),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    draft.refresh_from_db()
    assert draft.status == StartupAssessmentDraft.Status.SUBMITTED
    assert draft.startup_profile is not None
    assert draft.submitted_at is not None
    assert draft.submitted_profile_snapshot["startup_name"] == ("Assessment Workflow Startup")
    assert StartupProfile.objects.count() == 1
    assert StartupReadinessAssessment.objects.count() == 1
    assert StartupReadinessActionPlan.objects.count() == 1
    assert response.data["startup_profile"]["startup_name"] == ("Assessment Workflow Startup")
    assert response.data["readiness_assessment"]["status"] == "ready"
    assert response.data["recommendations"]["recommendation_count"] == 0


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_submit_updates_linked_profile(mock_generate):
    owner = make_user(username="assessment-update-owner")
    profile = make_profile(owner=owner, name="Original Startup")
    draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=profile,
        current_step=8,
        data={
            **valid_draft_data(),
            "startup_name": "Updated Startup",
            "founder_role": "managing_director",
        },
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(owner).post(
        reverse(
            "startup-assessment-draft-submit",
            kwargs={"draft_id": draft.id},
        ),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    profile.refresh_from_db()
    assert profile.startup_name == "Updated Startup"
    assert profile.profile_data["founder_role"] == "managing_director"
    assert StartupProfile.objects.count() == 1


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_submitted_draft_cannot_be_submitted_again(mock_generate):
    owner = make_user(username="assessment-resubmit-owner")
    draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        current_step=8,
        data=valid_draft_data(),
    )
    mock_generate.side_effect = recommendation_generation
    url = reverse(
        "startup-assessment-draft-submit",
        kwargs={"draft_id": draft.id},
    )

    first_response = authenticated_client(owner).post(
        url,
        {},
        format="json",
    )
    second_response = authenticated_client(owner).post(
        url,
        {},
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert StartupReadinessAssessment.objects.count() == 1
    assert StartupReadinessActionPlan.objects.count() == 1


def test_other_user_cannot_submit_draft():
    owner = make_user(username="assessment-submit-private-owner")
    other = make_user(username="assessment-submit-private-other")
    draft = StartupAssessmentDraft.objects.create(
        owner=owner,
        current_step=8,
        data=valid_draft_data(),
    )

    response = authenticated_client(other).post(
        reverse(
            "startup-assessment-draft-submit",
            kwargs={"draft_id": draft.id},
        ),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert draft.status == StartupAssessmentDraft.Status.DRAFT


def test_unauthenticated_draft_creation_is_rejected():
    response = APIClient().post(
        reverse("startup-assessment-draft-list"),
        {"data": valid_draft_data()},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StartupAssessmentDraft.objects.count() == 0


def test_repeated_linked_create_returns_existing_draft():
    owner = make_user(
        username="assessment-linked-idempotent",
    )
    profile = make_profile(
        owner=owner,
        name="Linked Idempotent Startup",
    )
    client = authenticated_client(owner)
    url = reverse("startup-assessment-draft-list")

    first_response = client.post(
        url,
        {
            "startup_profile_id": str(profile.id),
            "current_step": 2,
        },
        format="json",
    )
    second_response = client.post(
        url,
        {
            "startup_profile_id": str(profile.id),
            "current_step": 6,
            "data": {
                "startup_name": "Must not overwrite the draft",
            },
        },
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_200_OK
    assert second_response.data["id"] == first_response.data["id"]
    assert second_response.data["current_step"] == 2
    assert second_response.data["data"]["startup_name"] == "Linked Idempotent Startup"
    assert (
        StartupAssessmentDraft.objects.filter(
            owner=owner,
            startup_profile=profile,
            status=StartupAssessmentDraft.Status.DRAFT,
        ).count()
        == 1
    )


def test_repeated_onboarding_create_returns_existing_draft():
    owner = make_user(
        username="assessment-onboarding-idempotent",
    )
    client = authenticated_client(owner)
    url = reverse("startup-assessment-draft-list")

    first_response = client.post(
        url,
        {
            "current_step": 1,
            "data": {
                "startup_name": "Original Onboarding Draft",
            },
        },
        format="json",
    )
    second_response = client.post(
        url,
        {
            "current_step": 5,
            "data": {
                "startup_name": "Duplicate Request",
            },
        },
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_200_OK
    assert second_response.data["id"] == first_response.data["id"]
    assert second_response.data["current_step"] == 1
    assert second_response.data["data"]["startup_name"] == "Original Onboarding Draft"
    assert (
        StartupAssessmentDraft.objects.filter(
            owner=owner,
            startup_profile__isnull=True,
            status=StartupAssessmentDraft.Status.DRAFT,
        ).count()
        == 1
    )


def test_submitted_onboarding_draft_does_not_block_new_draft():
    owner = make_user(
        username="assessment-submitted-new-draft",
    )
    submitted = StartupAssessmentDraft.objects.create(
        owner=owner,
        status=StartupAssessmentDraft.Status.SUBMITTED,
        current_step=8,
        submitted_at=timezone.now(),
        data={
            "startup_name": "Previously Submitted Startup",
        },
    )

    response = authenticated_client(owner).post(
        reverse("startup-assessment-draft-list"),
        {
            "data": {
                "startup_name": "New Onboarding Startup",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["id"] != str(submitted.id)
    assert response.data["status"] == "draft"
    assert StartupAssessmentDraft.objects.count() == 2


@pytest.mark.parametrize(
    "linked",
    [False, True],
    ids=["onboarding", "linked-profile"],
)
def test_database_rejects_duplicate_open_draft(linked):
    owner = make_user(
        username=f"assessment-constraint-{linked}",
    )
    profile = (
        make_profile(
            owner=owner,
            name="Constraint Startup",
        )
        if linked
        else None
    )

    StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=profile,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            StartupAssessmentDraft.objects.create(
                owner=owner,
                startup_profile=profile,
            )

    assert (
        StartupAssessmentDraft.objects.filter(
            owner=owner,
            startup_profile=profile,
            status=StartupAssessmentDraft.Status.DRAFT,
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "linked",
    [False, True],
    ids=["onboarding", "linked-profile"],
)
def test_concurrent_create_reuses_single_open_draft(linked):
    owner = make_user(
        username=f"assessment-concurrent-{linked}",
    )
    profile = (
        make_profile(
            owner=owner,
            name="Concurrent Startup",
        )
        if linked
        else None
    )
    barrier = Barrier(2)

    def create_draft():
        close_old_connections()

        try:
            user_model = get_user_model()
            local_owner = user_model.objects.get(pk=owner.pk)
            local_profile = (
                StartupProfile.objects.get(pk=profile.pk) if profile is not None else None
            )

            barrier.wait(timeout=10)

            draft, created = get_or_create_startup_assessment_draft(
                owner=local_owner,
                startup_profile=local_profile,
                current_step=1,
                supplied_data={
                    "startup_name": "Concurrent Draft",
                },
            )
            return str(draft.id), created
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _index: create_draft(),
                range(2),
            )
        )

    draft_ids = {draft_id for draft_id, _created in results}
    creation_results = sorted(created for _draft_id, created in results)

    assert len(draft_ids) == 1
    assert creation_results == [False, True]
    assert (
        StartupAssessmentDraft.objects.filter(
            owner=owner,
            startup_profile=profile,
            status=StartupAssessmentDraft.Status.DRAFT,
        ).count()
        == 1
    )
