from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
)
from apps.recommendations.services.verification import (
    create_verification_submission,
    review_verification_submission,
    verification_gate_statuses,
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


def make_context():
    founder = User.objects.create_user(
        username="gate-founder",
        email="gate-founder@example.com",
        password="test-password",
        role=User.Role.FOUNDER,
    )
    reviewer = User.objects.create_user(
        username="gate-reviewer",
        email="gate-reviewer@example.com",
        password="test-password",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Gate Service Startup",
        stage=StartupProfile.Stage.MVP,
    )
    source = Source.objects.create(
        name="Gate service source",
        official_domain="gate-service.gov.in",
        listing_url="https://gate-service.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://gate-service.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash="gate-service-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name="Gate service authority",
    )
    scheme = Scheme.objects.create(
        canonical_name="Gate service scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash="gate-service-version",
        official_url="https://gate-service.gov.in/scheme/",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    manual_rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="manual.incubator_endorsement",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="Incubator endorsement is required.",
        manually_verified=True,
    )
    profile_rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="dpiit_recognized",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="DPIIT recognition is required.",
        manually_verified=True,
    )

    return (
        founder,
        reviewer,
        profile,
        version,
        manual_rule,
        profile_rule,
    )


def test_gate_status_lists_only_manual_rules():
    (
        _founder,
        _reviewer,
        profile,
        version,
        manual_rule,
        _profile_rule,
    ) = make_context()

    statuses = verification_gate_statuses(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 7, 23),
    )

    assert len(statuses) == 1
    assert statuses[0]["eligibility_rule_id"] == str(manual_rule.id)
    assert statuses[0]["status"] == "not_submitted"
    assert statuses[0]["resolved"] is False
    assert statuses[0]["submission"] is None
    assert statuses[0]["decision"] is None


def test_gate_status_tracks_pending_approved_and_future_rejection():
    (
        founder,
        reviewer,
        profile,
        version,
        manual_rule,
        _profile_rule,
    ) = make_context()

    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=manual_rule,
        submitted_by=founder,
        claim_value=True,
        claim_text="The endorsement has been obtained.",
    )

    pending = verification_gate_statuses(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 7, 23),
    )

    assert pending[0]["status"] == "pending"
    assert pending[0]["submission"]["id"] == str(submission.id)

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
        review_notes="Effective next month.",
        valid_from=date(2026, 8, 1),
    )

    current = verification_gate_statuses(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 7, 23),
    )

    assert current[0]["status"] == "approved"
    assert current[0]["resolved"] is True
    assert current[0]["decision"]["id"] == str(approval.id)

    future = verification_gate_statuses(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date(2026, 8, 1),
    )

    assert future[0]["status"] == "rejected"
    assert future[0]["resolved"] is False


def test_non_manual_rule_rejects_submission():
    (
        founder,
        _reviewer,
        profile,
        version,
        _manual_rule,
        profile_rule,
    ) = make_context()

    with pytest.raises(ValidationError) as exc_info:
        create_verification_submission(
            startup_profile=profile,
            scheme_version=version,
            eligibility_rule=profile_rule,
            submitted_by=founder,
            claim_value=True,
        )

    assert "eligibility_rule" in exc_info.value.message_dict
