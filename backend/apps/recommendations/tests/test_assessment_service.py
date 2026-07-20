from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.recommendations.models import EligibilityAssessment
from apps.recommendations.services import (
    create_eligibility_assessment,
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


def make_profile(
    *,
    owner,
    incorporation_date=date(2024, 1, 15),
    dpiit_recognized=True,
):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name="Audit Startup",
        stage=StartupProfile.Stage.MVP,
        incorporation_date=incorporation_date,
        dpiit_recognized=dpiit_recognized,
        profile_data={},
    )


def make_scheme_version(
    *,
    key: str = "assessment-service",
) -> SchemeVersion:
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
    authority = Authority.objects.create(
        name=f"Authority {key}",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Scheme {key}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
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
    scheme.current_version = version
    scheme.save(update_fields=["current_version", "updated_at"])

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
    EligibilityRule.objects.create(
        scheme_version=version,
        field_path="startup_age_months",
        operator=EligibilityRule.Operator.LESS_OR_EQUAL,
        expected_value=24,
        mandatory=True,
        rule_group="all",
        evidence_text="Startup age must not exceed 24 months.",
        manually_verified=True,
    )
    return version


def test_service_persists_exact_version_and_rule_snapshots():
    user = make_user(username="assessment-service-owner")
    profile = make_profile(owner=user)
    version = make_scheme_version()

    assessment = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=user,
        assessment_date=date(2026, 1, 15),
    )

    assert assessment.pk is not None
    assert assessment.scheme_version == version
    assert assessment.startup_profile == profile
    assert assessment.requested_by == user
    assert assessment.assessment_date == date(2026, 1, 15)
    assert assessment.result == EligibilityAssessment.Result.ELIGIBLE
    assert len(assessment.matched_rules) == 2
    assert assessment.failed_rules == []
    assert assessment.unknown_rules == []
    assert all(item["outcome"] == "pass" for item in assessment.matched_rules)
    assert EligibilityAssessment.objects.count() == 1


def test_assessment_date_controls_startup_age_result():
    user = make_user(username="assessment-date-owner")
    profile = make_profile(
        owner=user,
        incorporation_date=date(2024, 1, 15),
    )
    version = make_scheme_version(key="assessment-date")

    eligible = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=user,
        assessment_date=date(2026, 1, 15),
    )
    ineligible = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=user,
        assessment_date=date(2026, 1, 16),
    )

    assert eligible.result == EligibilityAssessment.Result.ELIGIBLE
    assert ineligible.result == EligibilityAssessment.Result.INELIGIBLE
    assert ineligible.failed_rules[0]["field_path"] == ("startup_age_months")
    assert ineligible.failed_rules[0]["actual_value"] == 25


def test_profile_snapshot_is_immutable_after_profile_edit():
    user = make_user(username="assessment-snapshot-owner")
    profile = make_profile(owner=user)
    version = make_scheme_version(key="assessment-snapshot")

    assessment = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=user,
        assessment_date=date(2026, 1, 15),
    )
    original_snapshot = assessment.profile_snapshot

    profile.startup_name = "Edited Startup"
    profile.dpiit_recognized = False
    profile.profile_data = {
        "client_supplied": "changed later",
    }
    profile.save()

    assessment.refresh_from_db()

    assert assessment.profile_snapshot == original_snapshot
    assert assessment.profile_snapshot["startup_name"] == ("Audit Startup")
    assert assessment.profile_snapshot["dpiit_recognized"] is True
    assert assessment.profile_snapshot["profile_data"] == {}
