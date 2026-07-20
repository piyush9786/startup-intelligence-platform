from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
)
from apps.recommendations.services import (
    RANKING_VERSION,
    generate_recommendations,
)
from apps.schemes.models import (
    Authority,
    EligibilityRule,
    Scheme,
    SchemeVersion,
)
from apps.sources.models import Source, SourceDocument
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db


def make_user(*, username: str):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
    )


def make_profile(*, owner):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name="Recommendation Startup",
        stage=StartupProfile.Stage.MVP,
        incorporation_date=date(2025, 1, 15),
        dpiit_recognized=True,
        profile_data={},
    )


def make_scheme(
    *,
    key: str,
    name: str,
    expected_dpiit=True,
    application_status=(SchemeVersion.ApplicationStatus.UNKNOWN),
    lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
    with_current_version=True,
    with_rule=True,
):
    authority = Authority.objects.create(
        name=f"Authority {key}",
    )
    scheme = Scheme.objects.create(
        canonical_name=name,
        authority=authority,
        lifecycle_status=lifecycle_status,
    )

    if not with_current_version:
        return scheme

    source = Source.objects.create(
        name=f"Source {key}",
        official_domain=f"{key}.example.gov.in",
        listing_url=f"https://{key}.example.gov.in",
        authority_tier=(Source.AuthorityTier.OFFICIAL_AUTHORITY),
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://{key}.example.gov.in/source",
        content_hash=f"{key}-document-hash",
        retrieved_at=timezone.now(),
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"{key}-version-hash",
        official_url=f"https://{key}.example.gov.in/scheme",
        application_url=f"https://{key}.example.gov.in/apply",
        application_status=application_status,
        verification_status=verification_status,
    )
    if with_rule:
        EligibilityRule.objects.create(
            scheme_version=version,
            field_path="dpiit_recognized",
            operator=EligibilityRule.Operator.EQUALS,
            expected_value=expected_dpiit,
            mandatory=True,
            rule_group="all",
            evidence_text="DPIIT recognition rule.",
            manually_verified=True,
        )

    scheme.current_version = version
    scheme.save(
        update_fields=[
            "current_version",
            "updated_at",
        ]
    )
    return scheme


def test_generation_evaluates_all_and_recommends_actionable_only():
    user = make_user(username="generation-owner")
    profile = make_profile(owner=user)

    open_scheme = make_scheme(
        key="open",
        name="Open Scheme",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
    )
    unknown_scheme = make_scheme(
        key="unknown",
        name="Unknown Scheme",
    )
    make_scheme(
        key="upcoming",
        name="Upcoming Scheme",
        application_status=(SchemeVersion.ApplicationStatus.UPCOMING),
    )
    make_scheme(
        key="closed",
        name="Closed Scheme",
        application_status=(SchemeVersion.ApplicationStatus.CLOSED),
    )
    make_scheme(
        key="ineligible",
        name="Ineligible Scheme",
        expected_dpiit=False,
    )

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 20),
    )

    assert len(generation.assessments) == 5
    assert len(generation.recommendations) == 2
    assert len(generation.excluded_schemes) == 3
    assert EligibilityAssessment.objects.count() == 5
    assert Recommendation.objects.count() == 2

    first, second = generation.recommendations
    assert first.scheme_version.scheme == open_scheme
    assert second.scheme_version.scheme == unknown_scheme
    assert first.rank == 1
    assert second.rank == 2
    assert first.score == Decimal("1.000000")
    assert second.score == Decimal("0.950000")
    assert first.ranking_version == RANKING_VERSION
    assert first.generation_id == second.generation_id == generation.generation_id


def test_equal_scores_use_scheme_name_tie_break():
    user = make_user(username="tie-break-owner")
    profile = make_profile(owner=user)

    make_scheme(
        key="beta",
        name="Beta Scheme",
    )
    make_scheme(
        key="alpha",
        name="Alpha Scheme",
    )

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 20),
    )

    assert [item.scheme_version.scheme.canonical_name for item in generation.recommendations] == [
        "Alpha Scheme",
        "Beta Scheme",
    ]
    assert [item.rank for item in generation.recommendations] == [1, 2]


def test_repeated_generation_replaces_current_recommendations():
    user = make_user(username="replacement-owner")
    profile = make_profile(owner=user)

    first_scheme = make_scheme(
        key="replacement-first",
        name="First Scheme",
    )
    second_scheme = make_scheme(
        key="replacement-second",
        name="Second Scheme",
    )

    first_generation = generate_recommendations(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 20),
    )
    assert Recommendation.objects.count() == 2

    second_scheme.current_version.application_status = SchemeVersion.ApplicationStatus.UPCOMING
    second_scheme.current_version.save(
        update_fields=[
            "application_status",
            "updated_at",
        ]
    )

    second_generation = generate_recommendations(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 21),
    )

    assert first_generation.generation_id != (second_generation.generation_id)
    assert Recommendation.objects.count() == 1
    current = Recommendation.objects.get()
    assert current.scheme_version.scheme == first_scheme
    assert current.generation_id == (second_generation.generation_id)
    assert not Recommendation.objects.filter(
        generation_id=first_generation.generation_id,
    ).exists()
    assert EligibilityAssessment.objects.count() == 4


def test_only_active_verified_current_versions_are_assessed():
    user = make_user(username="scope-owner")
    profile = make_profile(owner=user)

    make_scheme(
        key="scope-active",
        name="Active Verified Scheme",
    )
    make_scheme(
        key="scope-inactive",
        name="Inactive Scheme",
        lifecycle_status=(Scheme.LifecycleStatus.INACTIVE),
    )
    make_scheme(
        key="scope-unverified",
        name="Unverified Scheme",
        verification_status=(SchemeVersion.VerificationStatus.REVIEW_REQUIRED),
    )
    make_scheme(
        key="scope-no-current",
        name="No Current Version Scheme",
        with_current_version=False,
    )

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=user,
        assessment_date=date(2026, 7, 20),
    )

    assert len(generation.assessments) == 1
    assert len(generation.recommendations) == 1
    assert EligibilityAssessment.objects.count() == 1
