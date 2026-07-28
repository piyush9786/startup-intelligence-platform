from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.startups.models import (
    StartupProfile,
    StartupReadinessAssessment,
)
from apps.startups.services import (
    create_startup_readiness_assessment,
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
            "A technology startup solving a clearly "
            "defined customer problem with a scalable "
            "digital product."
        ),
        incorporation_type="private_limited",
        incorporation_date=date(2025, 1, 15),
        state="Karnataka",
        district="Bengaluru Urban",
        stage=StartupProfile.Stage.MVP,
        sectors=["software"],
        technologies=["artificial intelligence"],
        founder_categories=[],
        founder_gender="",
        dpiit_recognized=True,
        udyam_registered=False,
        annual_turnover=Decimal("1000000.00"),
        revenue_stage="early_revenue",
        funding_required=Decimal("5000000.00"),
        funding_purpose=("Product development and market expansion."),
        team_size=8,
        profile_data={},
    )


def test_service_persists_evaluation_and_snapshot():
    user = make_user(username="readiness-service")
    profile = make_profile(
        owner=user,
        name="Readiness Service Startup",
    )

    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 21),
    )

    assert assessment.requested_by == user
    assert assessment.startup_profile == profile
    assert assessment.assessment_date == date(
        2026,
        7,
        21,
    )
    assert assessment.status == (StartupReadinessAssessment.Status.READY)
    assert assessment.score == 100
    assert assessment.critical_score == 100
    assert assessment.recommended_score == 100
    assert assessment.engine_version == ("startup-readiness-v1")
    assert assessment.profile_snapshot["id"] == str(profile.id)
    assert assessment.profile_snapshot["incorporation_date"] == "2025-01-15"
    assert assessment.profile_snapshot["annual_turnover"] == "1000000.00"
    assert assessment.blocking_findings == []
    assert {item["code"] for item in assessment.findings} >= {
        "startup_name",
        "incorporation_date",
        "dpiit_recognized",
        "funding_plan",
    }


def test_service_retains_historical_assessments():
    user = make_user(username="readiness-history")
    profile = make_profile(
        owner=user,
        name="Readiness History Startup",
    )

    first = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 20),
    )
    profile.district = ""
    profile.save(
        update_fields=[
            "district",
            "updated_at",
        ]
    )
    second = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 21),
    )

    assessments = list(
        StartupReadinessAssessment.objects.filter(
            startup_profile=profile,
        )
    )
    assert len(assessments) == 2
    assert assessments == [second, first]
    assert first.profile_snapshot["district"] == ("Bengaluru Urban")
    assert second.profile_snapshot["district"] == ""
    assert second.status == (StartupReadinessAssessment.Status.READY_WITH_RECOMMENDATIONS)


def test_service_persists_blocking_findings():
    user = make_user(username="readiness-blocked")
    profile = make_profile(
        owner=user,
        name="Readiness Blocked Startup",
    )
    profile.dpiit_recognized = None
    profile.save(
        update_fields=[
            "dpiit_recognized",
            "updated_at",
        ]
    )

    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 21),
    )

    assert assessment.status == (StartupReadinessAssessment.Status.BLOCKED)
    assert {item["code"] for item in assessment.blocking_findings} == {"dpiit_recognized"}
    assert assessment.score < 100
