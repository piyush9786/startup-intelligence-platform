from datetime import date

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
)
from apps.recommendations.services.explanation import (
    build_eligibility_explanation,
)
from apps.recommendations.services.recommendations import (
    generate_recommendations,
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
from apps.sources.models import (
    Source,
    SourceDocument,
)
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db


def test_verified_decision_provenance_is_persisted_in_outputs():
    founder = User.objects.create_user(
        username="provenance-founder",
        email="provenance-founder@example.com",
        password="test-password",
        role=User.Role.FOUNDER,
    )
    reviewer = User.objects.create_user(
        username="provenance-reviewer",
        email="provenance-reviewer@example.com",
        password="test-password",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Provenance Startup",
        stage=StartupProfile.Stage.MVP,
    )
    source = Source.objects.create(
        name="Provenance official source",
        official_domain="provenance.gov.in",
        listing_url=(
            "https://provenance.gov.in/schemes/"
        ),
        authority_tier=(
            Source.AuthorityTier.OFFICIAL_PROGRAMME
        ),
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=(
            "https://provenance.gov.in/scheme.pdf"
        ),
        mime_type="application/pdf",
        content_hash="provenance-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name="Provenance authority",
    )
    scheme = Scheme.objects.create(
        canonical_name="Provenance scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash="provenance-version",
        official_url=(
            "https://provenance.gov.in/scheme/"
        ),
        application_status=(
            SchemeVersion.ApplicationStatus.OPEN
        ),
        verification_status=(
            SchemeVersion.VerificationStatus.VERIFIED
        ),
    )
    scheme.current_version = version
    scheme.save(
        update_fields=[
            "current_version",
        ]
    )

    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path=(
            "manual.incubator_endorsement"
        ),
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text=(
            "Official incubator endorsement is required."
        ),
        manually_verified=True,
    )

    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
        claim_text=(
            "The startup has the required endorsement."
        ),
    )
    approval = review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=(
            EligibilityVerificationDecision
            .Outcome
            .APPROVED
        ),
        verified_value=True,
        review_notes="Endorsement verified.",
        valid_from=date(2026, 7, 1),
        expires_on=date(2026, 12, 31),
    )

    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=founder,
        assessment_date=date(2026, 7, 23),
    )

    assert len(generation.assessments) == 1
    assert len(generation.recommendations) == 1

    assessment = generation.assessments[0]
    recommendation = generation.recommendations[0]

    expected_provenance = [
        {
            "rule_id": str(rule.id),
            "field_path": (
                "manual.incubator_endorsement"
            ),
            "outcome": "pass",
            "decision_id": str(approval.id),
            "submission_id": str(submission.id),
            "valid_from": "2026-07-01",
            "expires_on": "2026-12-31",
            "message": (
                "Incubator endorsement was evaluated "
                "using reviewer-approved evidence."
            ),
        }
    ]

    explanation = build_eligibility_explanation(
        assessment,
    )

    assert explanation["version"] == (
        "eligibility-explanation-v2"
    )
    assert (
        explanation["verification_provenance"]
        == expected_provenance
    )
    assert (
        recommendation.evidence_snapshot[
            "verification_provenance"
        ]
        == expected_provenance
    )
    assert (
        generation
        .generation_run
        .recommendation_snapshot[0][
            "eligibility_explanation"
        ][
            "verification_provenance"
        ]
        == expected_provenance
    )
