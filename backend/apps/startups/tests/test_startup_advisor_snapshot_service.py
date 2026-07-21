import uuid
from copy import deepcopy
from datetime import date

import pytest

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services import (
    RecommendationSetIntegrityError,
    generate_recommendations,
)
from apps.recommendations.tests.test_recommendation_api import (
    make_profile,
    make_scheme,
    make_user,
)
from apps.schemes.models import SchemeVersion
from apps.startups.models import (
    StartupAdvisorSnapshot,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.services import (
    ADVISOR_SNAPSHOT_VERSION,
    create_startup_advisor_snapshot,
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)

pytestmark = pytest.mark.django_db


def create_guidance(*, owner, name: str):
    profile = make_profile(
        owner=owner,
        name=name,
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
    make_scheme(key=f"snapshot-{owner.username}")
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


def test_service_persists_complete_immutable_snapshot():
    owner = make_user(username="advisor-snapshot-service-owner")
    (
        profile,
        readiness_assessment,
        action_plan,
        generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot Service Startup",
    )

    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    assert snapshot.requested_by == owner
    assert snapshot.startup_profile == profile
    assert snapshot.readiness_assessment == readiness_assessment
    assert snapshot.readiness_action_plan == action_plan
    assert snapshot.recommendation_generation_run == generation_run
    assert snapshot.has_readiness_assessment is True
    assert snapshot.has_action_plan is True
    assert snapshot.has_recommendation_generation is True
    assert snapshot.recommendation_count == 1
    assert snapshot.snapshot_version == ADVISOR_SNAPSHOT_VERSION
    assert snapshot.profile_snapshot["id"] == str(profile.id)
    assert snapshot.readiness_snapshot["id"] == str(readiness_assessment.id)
    assert snapshot.action_plan_snapshot["id"] == str(action_plan.id)
    assert snapshot.recommendation_generation_snapshot["generation_id"] == str(generation_run.id)
    assert snapshot.recommendations_snapshot[0]["id"] == str(recommendation.id)


def test_service_persists_explicit_empty_sources():
    owner = make_user(username="advisor-snapshot-service-empty")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot Empty Startup",
    )

    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    assert snapshot.has_readiness_assessment is False
    assert snapshot.readiness_assessment is None
    assert snapshot.readiness_snapshot == {}
    assert snapshot.has_action_plan is False
    assert snapshot.readiness_action_plan is None
    assert snapshot.action_plan_snapshot == {}
    assert snapshot.has_recommendation_generation is False
    assert snapshot.recommendation_generation_run is None
    assert snapshot.recommendation_generation_snapshot == {}
    assert snapshot.recommendation_count == 0
    assert snapshot.recommendations_snapshot == []


def test_service_selects_latest_sources_independently():
    owner = make_user(username="advisor-snapshot-service-latest")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot Latest Startup",
    )
    first_assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )
    only_plan = create_startup_readiness_action_plan(
        source_assessment=first_assessment,
        requested_by=owner,
    )
    latest_assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    assert snapshot.readiness_assessment == latest_assessment
    assert snapshot.readiness_action_plan == only_plan
    assert snapshot.readiness_action_plan.source_assessment == (first_assessment)


def test_service_retains_historical_snapshots():
    owner = make_user(username="advisor-snapshot-service-history")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot History Startup",
    )

    first = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    profile.startup_name = "Advisor Snapshot History Renamed"
    profile.save(
        update_fields=[
            "startup_name",
            "updated_at",
        ]
    )
    second = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    assert StartupAdvisorSnapshot.objects.count() == 2
    assert first.pk != second.pk
    assert first.profile_snapshot["startup_name"] == ("Advisor Snapshot History Startup")
    assert second.profile_snapshot["startup_name"] == ("Advisor Snapshot History Renamed")


def test_persisted_json_does_not_change_with_sources():
    owner = make_user(username="advisor-snapshot-service-immutable")
    (
        profile,
        readiness_assessment,
        action_plan,
        generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot Immutable Startup",
    )
    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    stored = {
        "profile": deepcopy(snapshot.profile_snapshot),
        "readiness": deepcopy(snapshot.readiness_snapshot),
        "action_plan": deepcopy(snapshot.action_plan_snapshot),
        "generation": deepcopy(snapshot.recommendation_generation_snapshot),
        "recommendations": deepcopy(snapshot.recommendations_snapshot),
    }

    profile.startup_name = "Changed profile"
    profile.save(update_fields=["startup_name", "updated_at"])
    readiness_assessment.summary = "Changed assessment"
    readiness_assessment.save(update_fields=["summary", "updated_at"])
    action_plan.items = []
    action_plan.save(update_fields=["items", "updated_at"])
    generation_run.profile_snapshot = {"changed": True}
    generation_run.save(update_fields=["profile_snapshot", "updated_at"])
    recommendation.evidence_snapshot = {"changed": True}
    recommendation.save(update_fields=["evidence_snapshot", "updated_at"])

    snapshot.refresh_from_db()

    assert snapshot.profile_snapshot == stored["profile"]
    assert snapshot.readiness_snapshot == stored["readiness"]
    assert snapshot.action_plan_snapshot == stored["action_plan"]
    assert snapshot.recommendation_generation_snapshot == stored["generation"]
    assert snapshot.recommendations_snapshot == stored["recommendations"]


def test_zero_result_generation_is_captured_as_available():
    owner = make_user(username="advisor-snapshot-service-zero")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot Zero Startup",
    )
    make_scheme(key="advisor-snapshot-zero")
    version = SchemeVersion.objects.get()
    version.application_status = SchemeVersion.ApplicationStatus.UPCOMING
    version.save(
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

    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    assert snapshot.has_recommendation_generation is True
    assert snapshot.recommendation_generation_run is not None
    assert snapshot.recommendation_count == 0
    assert snapshot.recommendations_snapshot == []


def test_integrity_failure_rolls_back_snapshot_write():
    owner = make_user(username="advisor-snapshot-service-conflict")
    (
        profile,
        _readiness_assessment,
        _action_plan,
        _generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot Conflict Startup",
    )
    recommendation.generation_id = uuid.uuid4()
    recommendation.save(
        update_fields=[
            "generation_id",
            "updated_at",
        ]
    )

    with pytest.raises(
        RecommendationSetIntegrityError,
        match="do not match the run ID",
    ):
        create_startup_advisor_snapshot(
            startup_profile=profile,
            requested_by=owner,
        )

    assert StartupAdvisorSnapshot.objects.count() == 0


def test_service_only_adds_advisor_snapshot_record():
    owner = make_user(username="advisor-snapshot-service-write")
    (
        profile,
        _readiness_assessment,
        _action_plan,
        _generation_run,
        _recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot Write Boundary Startup",
    )
    counts_before = {
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }

    create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )

    counts_after = {
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }

    assert counts_after == counts_before
    assert StartupAdvisorSnapshot.objects.count() == 1
