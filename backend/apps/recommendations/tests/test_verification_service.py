from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
    EligibilityVerificationSubmission,
)
from apps.recommendations.services.verification import (
    approved_verification_values,
    create_verification_submission,
    review_verification_submission,
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


def make_user(
    username: str,
    *,
    role: str = User.Role.FOUNDER,
    is_staff: bool = False,
) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
        is_staff=is_staff,
    )


def make_context():
    source = Source.objects.create(
        name="Verification source",
        official_domain="verification.gov.in",
        listing_url="https://verification.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://verification.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash="verification-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name="Verification authority",
    )
    scheme = Scheme.objects.create(
        canonical_name="Verification scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash="verification-version",
        official_url="https://verification.gov.in/scheme/",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version"])

    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="manual.incubator_endorsement",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="Official incubator endorsement is required.",
        manually_verified=True,
    )
    return version, rule


def test_submission_supersedes_current_submission_atomically():
    founder = make_user("submission-founder")
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Submission Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()

    first = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=False,
        claim_text="Initial submission.",
    )
    second = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
        claim_text="Corrected submission.",
    )

    first.refresh_from_db()

    assert first.is_current is False
    assert second.is_current is True
    assert second.supersedes_id == first.id
    assert (
        EligibilityVerificationSubmission.objects.filter(
            startup_profile=profile,
            eligibility_rule=rule,
            is_current=True,
        ).count()
        == 1
    )


def test_non_owner_cannot_submit_for_startup():
    founder = make_user("owner-founder")
    outsider = make_user("outsider-founder")
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Owner Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()

    with pytest.raises(ValidationError):
        create_verification_submission(
            startup_profile=profile,
            scheme_version=version,
            eligibility_rule=rule,
            submitted_by=outsider,
            claim_value=True,
        )


def test_only_reviewer_or_admin_can_create_decision():
    founder = make_user("review-founder")
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Review Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()
    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
    )

    with pytest.raises(ValidationError):
        review_verification_submission(
            submission=submission,
            reviewer=founder,
            outcome=EligibilityVerificationDecision.Outcome.APPROVED,
            verified_value=True,
            valid_from=date(2026, 7, 23),
        )


def test_approved_value_uses_only_latest_valid_decision():
    founder = make_user("approved-founder")
    reviewer = make_user(
        "approved-reviewer",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Approved Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()
    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
    )

    approval = review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        valid_from=date(2026, 7, 1),
        expires_on=date(2026, 7, 31),
    )

    values = approved_verification_values(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 7, 23),
    )

    assert values[str(rule.id)] == {
        "value": True,
        "decision_id": str(approval.id),
        "submission_id": str(submission.id),
        "valid_from": "2026-07-01",
        "expires_on": "2026-07-31",
    }

    review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.REJECTED,
        verified_value=None,
        review_notes="Later evidence review failed.",
        valid_from=date(2026, 7, 23),
    )

    assert (
        approved_verification_values(
            startup_profile=profile,
            scheme_version=version,
            as_of_date=date(2026, 7, 23),
        )
        == {}
    )


def test_expired_approval_is_not_returned():
    founder = make_user("expired-founder")
    reviewer = make_user(
        "expired-reviewer",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Expired Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()
    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
    )
    review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        valid_from=date(2026, 6, 1),
        expires_on=date(2026, 6, 30),
    )

    assert (
        approved_verification_values(
            startup_profile=profile,
            scheme_version=version,
            as_of_date=date(2026, 7, 23),
        )
        == {}
    )


def test_future_decision_does_not_override_current_approval():
    founder = make_user("future-decision-founder")
    reviewer = make_user(
        "future-decision-reviewer",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Future Decision Startup",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context()
    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
    )

    approval = review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        valid_from=date(2026, 7, 1),
    )
    review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.REJECTED,
        verified_value=None,
        review_notes="Rejection becomes effective next month.",
        valid_from=date(2026, 8, 1),
    )

    current_values = approved_verification_values(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 7, 23),
    )

    assert current_values[str(rule.id)] == {
        "value": True,
        "decision_id": str(approval.id),
        "submission_id": str(submission.id),
        "valid_from": "2026-07-01",
        "expires_on": None,
    }

    assert (
        approved_verification_values(
            startup_profile=profile,
            scheme_version=version,
            as_of_date=date(2026, 8, 1),
        )
        == {}
    )
