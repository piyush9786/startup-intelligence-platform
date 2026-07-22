from datetime import date

import pytest

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services import (
    generate_recommendations,
    get_current_recommendation_set,
)
from apps.recommendations.tests.test_recommendation_api import (
    make_profile,
    make_scheme,
    make_user,
)
from apps.schemes.models import SchemeVersion

pytestmark = pytest.mark.django_db


def test_zero_recommendation_generation_is_persisted():
    owner = make_user(username="zero-run-owner")
    profile = make_profile(
        owner=owner,
        name="Zero Run Startup",
    )
    make_scheme(key="zero-run")
    version = SchemeVersion.objects.get()
    version.application_status = SchemeVersion.ApplicationStatus.UPCOMING
    version.save(
        update_fields=[
            "application_status",
            "updated_at",
        ]
    )

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )

    run = generation.generation_run
    assert run.is_current is True
    assert run.assessed_scheme_count == 1
    assert run.recommendation_count == 0
    assert len(run.excluded_schemes) == 1
    assert run.recommendation_snapshot == []
    assert run.excluded_schemes[0]["eligibility_explanation"]["result"] == (
        "eligible"
    )
    assert Recommendation.objects.count() == 0
    assert (
        EligibilityAssessment.objects.filter(
            generation_run=run,
        ).count()
        == 1
    )

    current_set = get_current_recommendation_set(
        startup_profile=profile,
    )
    assert current_set.has_generation is True
    assert current_set.generation_id == run.id
    assert current_set.recommendations == ()


def test_repeated_generation_retains_run_history():
    owner = make_user(username="run-history-owner")
    profile = make_profile(
        owner=owner,
        name="Run History Startup",
    )
    make_scheme(key="run-history")

    first = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )
    second = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    assert RecommendationGenerationRun.objects.count() == 2
    first.generation_run.refresh_from_db()
    second.generation_run.refresh_from_db()
    assert first.generation_run.is_current is False
    assert second.generation_run.is_current is True
    assert first.generation_run.recommendation_count == 1
    assert len(first.generation_run.recommendation_snapshot) == 1
    assert Recommendation.objects.count() == 1
    assert Recommendation.objects.get().generation_run == (second.generation_run)


def test_generation_assessments_are_linked_to_run():
    owner = make_user(username="linked-run-owner")
    profile = make_profile(
        owner=owner,
        name="Linked Run Startup",
    )
    make_scheme(key="linked-run-one")
    make_scheme(key="linked-run-two")

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )

    assert len(generation.assessments) == 2
    assert {item.generation_run_id for item in generation.assessments} == {
        generation.generation_id,
    }
    assert generation.generation_run.profile_snapshot["startup_name"] == profile.startup_name
