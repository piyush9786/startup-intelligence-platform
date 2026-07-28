from datetime import date

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
)
from apps.recommendations.services.assessment import (
    create_eligibility_assessment,
)
from apps.recommendations.services.verification import (
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


def test_rules_v5_consumes_only_latest_approved_verification():
    founder = User.objects.create_user(
        username="rules-v5-founder",
        email="rules-v5-founder@example.com",
        password="test-password",
        role=User.Role.FOUNDER,
    )
    reviewer = User.objects.create_user(
        username="rules-v5-reviewer",
        email="rules-v5-reviewer@example.com",
        password="test-password",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Rules v5 Startup",
        stage=StartupProfile.Stage.MVP,
    )
    source = Source.objects.create(
        name="Rules v5 official source",
        official_domain="rules-v5.gov.in",
        listing_url="https://rules-v5.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://rules-v5.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash="rules-v5-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name="Rules v5 authority",
    )
    scheme = Scheme.objects.create(
        canonical_name="Rules v5 scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash="rules-v5-version",
        official_url="https://rules-v5.gov.in/scheme/",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="manual.incubator_endorsement",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="Official incubator endorsement is required.",
        manually_verified=True,
    )

    before = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=founder,
        assessment_date=date(2026, 7, 23),
    )

    assert before.result == "verification_required"
    assert before.engine_version == "rules-v5"

    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
        claim_text="The startup has the required endorsement.",
    )
    approval = review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        review_notes="Endorsement verified.",
        valid_from=date(2026, 7, 1),
    )

    approved = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=founder,
        assessment_date=date(2026, 7, 23),
    )

    assert approved.result == "eligible"
    assert approved.engine_version == "rules-v5"
    assert len(approved.matched_rules) == 1
    assert approved.matched_rules[0]["rule_id"] == str(rule.id)
    assert approved.matched_rules[0]["actual_value"] is True
    assert approved.matched_rules[0]["verification"] == {
        "decision_id": str(approval.id),
        "submission_id": str(submission.id),
        "valid_from": "2026-07-01",
        "expires_on": None,
    }

    review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.REJECTED,
        verified_value=None,
        review_notes="Later review rejected the evidence.",
        valid_from=date(2026, 7, 23),
    )

    after_rejection = create_eligibility_assessment(
        startup_profile=profile,
        scheme_version=version,
        requested_by=founder,
        assessment_date=date(2026, 7, 23),
    )

    assert after_rejection.result == "verification_required"
    assert after_rejection.matched_rules == []
