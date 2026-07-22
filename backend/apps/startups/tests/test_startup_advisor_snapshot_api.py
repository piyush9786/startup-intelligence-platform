import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services import generate_recommendations
from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_scheme,
    make_user,
)
from apps.schemes.models import SchemeVersion
from apps.startups.models import (
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.services import (
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)

pytestmark = pytest.mark.django_db


def advisor_url(profile_id):
    return reverse("startup-advisor-current") + f"?startup_profile_id={profile_id}"


def create_guidance(*, owner, name: str):
    profile = make_profile(
        owner=owner,
        name=name,
    )
    profile.legal_name = f"{name} Private Limited"
    profile.state = "Karnataka"
    profile.district = "Bengaluru Urban"
    profile.save(
        update_fields=[
            "legal_name",
            "state",
            "district",
            "updated_at",
        ]
    )
    readiness_assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    action_plan = create_startup_readiness_action_plan(
        source_assessment=readiness_assessment,
        requested_by=owner,
    )
    make_scheme(
        key=f"advisor-{owner.username}",
    )
    generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    generation_run = RecommendationGenerationRun.objects.get(
        startup_profile=profile,
        is_current=True,
    )
    recommendation = Recommendation.objects.get(
        generation_run=generation_run,
    )
    return (
        profile,
        readiness_assessment,
        action_plan,
        generation_run,
        recommendation,
    )


def test_owner_receives_complete_current_advisor_snapshot():
    owner = make_user(username="advisor-owner")
    (
        profile,
        readiness_assessment,
        action_plan,
        generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Startup",
    )

    response = authenticated_client(owner).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile"] == {
        "id": str(profile.id),
        "startup_name": profile.startup_name,
        "legal_name": profile.legal_name,
        "stage": profile.stage,
        "state": profile.state,
        "district": profile.district,
    }
    assert response.data["readiness"]["has_assessment"] is True
    assert response.data["readiness"]["assessment"]["id"] == str(readiness_assessment.id)
    assert response.data["action_plan"]["has_action_plan"] is True
    assert response.data["action_plan"]["action_plan"]["id"] == str(action_plan.id)
    assert response.data["recommendations"]["has_generation"] is True
    assert response.data["recommendations"]["generation"]["generation_id"] == str(generation_run.id)
    assert response.data["recommendations"]["recommendation_count"] == 1
    assert response.data["recommendations"]["recommendations"][0]["id"] == str(recommendation.id)


def test_profile_without_guidance_returns_explicit_empty_sections():
    owner = make_user(username="advisor-empty-owner")
    profile = make_profile(
        owner=owner,
        name="Advisor Empty Startup",
    )

    response = authenticated_client(owner).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["readiness"] == {
        "has_assessment": False,
        "assessment": None,
    }
    assert response.data["action_plan"] == {
        "has_action_plan": False,
        "action_plan": None,
    }
    assert response.data["recommendations"] == {
        "has_generation": False,
        "generation": None,
        "recommendation_count": 0,
        "recommendations": [],
    }


def test_zero_result_generation_is_available_not_missing():
    owner = make_user(username="advisor-zero-owner")
    profile = make_profile(
        owner=owner,
        name="Advisor Zero Startup",
    )
    make_scheme(key="advisor-zero")
    scheme_version = SchemeVersion.objects.get()
    scheme_version.application_status = SchemeVersion.ApplicationStatus.UPCOMING
    scheme_version.save(
        update_fields=[
            "application_status",
            "updated_at",
        ]
    )
    generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    response = authenticated_client(owner).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["recommendations"]["has_generation"] is True
    assert response.data["recommendations"]["generation"] is not None
    assert response.data["recommendations"]["recommendation_count"] == 0
    assert response.data["recommendations"]["recommendations"] == []

    generation = response.data["recommendations"]["generation"]
    assert generation["assessed_scheme_count"] == 1
    assert generation["excluded_scheme_count"] == 1
    assert len(generation["excluded_schemes"]) == 1
    assert (
        generation["excluded_schemes"][0]["reason"]
        == "application_status:upcoming"
    )


def test_other_user_cannot_access_advisor_snapshot():
    owner = make_user(username="advisor-private-owner")
    other = make_user(username="advisor-private-other")
    profile = make_profile(
        owner=owner,
        name="Advisor Private Startup",
    )

    response = authenticated_client(other).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_access_another_users_advisor_snapshot():
    owner = make_user(username="advisor-staff-owner")
    staff = make_user(
        username="advisor-staff",
        is_staff=True,
    )
    (
        profile,
        readiness_assessment,
        _action_plan,
        _generation_run,
        _recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Staff Startup",
    )

    response = authenticated_client(staff).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["readiness"]["assessment"]["id"] == str(readiness_assessment.id)


def test_missing_profile_id_returns_400():
    owner = make_user(username="advisor-missing-owner")

    response = authenticated_client(owner).get(reverse("startup-advisor-current"))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in response.data


def test_unknown_profile_returns_404():
    owner = make_user(username="advisor-unknown-owner")

    response = authenticated_client(owner).get(advisor_url("00000000-0000-0000-0000-000000000001"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_inconsistent_current_recommendation_set_returns_409():
    owner = make_user(username="advisor-conflict-owner")
    (
        profile,
        _readiness_assessment,
        _action_plan,
        _generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Conflict Startup",
    )
    recommendation.generation_id = uuid.uuid4()
    recommendation.save(
        update_fields=[
            "generation_id",
            "updated_at",
        ]
    )

    response = authenticated_client(owner).get(advisor_url(profile.id))

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "do not match the run ID" in response.data["detail"]


def test_snapshot_is_read_only_and_uses_persisted_records():
    owner = make_user(username="advisor-stored-owner")
    (
        profile,
        readiness_assessment,
        action_plan,
        generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Stored Startup",
    )
    stored_profile_snapshot = readiness_assessment.profile_snapshot
    stored_action_snapshot = action_plan.source_assessment_snapshot
    stored_items = action_plan.items
    stored_run_snapshot = generation_run.profile_snapshot
    stored_evidence = recommendation.evidence_snapshot

    profile.description = "Changed after all guidance was generated."
    profile.save(
        update_fields=[
            "description",
            "updated_at",
        ]
    )
    readiness_assessment.findings = []
    readiness_assessment.summary = "Changed after plan generation."
    readiness_assessment.save(
        update_fields=[
            "findings",
            "summary",
            "updated_at",
        ]
    )

    counts_before = {
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }

    response = authenticated_client(owner).get(advisor_url(profile.id))

    counts_after = {
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }

    assert response.status_code == status.HTTP_200_OK
    assert response.data["readiness"]["assessment"]["profile_snapshot"] == stored_profile_snapshot
    assert (
        response.data["action_plan"]["action_plan"]["source_assessment_snapshot"]
        == stored_action_snapshot
    )
    assert response.data["action_plan"]["action_plan"]["items"] == stored_items
    assert response.data["recommendations"]["generation"]["profile_snapshot"] == stored_run_snapshot
    assert (
        response.data["recommendations"]["recommendations"][0]["evidence_snapshot"]
        == stored_evidence
    )
    assert counts_after == counts_before


def test_unauthenticated_request_is_rejected():
    response = APIClient().get(advisor_url(uuid.uuid4()))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
