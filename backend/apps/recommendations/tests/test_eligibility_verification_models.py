from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
    EligibilityVerificationEvidence,
    EligibilityVerificationSubmission,
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
    *,
    username: str,
    role: str = User.Role.FOUNDER,
) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
    )


def make_scheme_context(*, suffix: str) -> tuple[SchemeVersion, EligibilityRule]:
    source = Source.objects.create(
        name=f"Official source {suffix}",
        official_domain=f"official-{suffix}.gov.in",
        listing_url=f"https://official-{suffix}.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://official-{suffix}.gov.in/scheme.pdf",
        title=f"Scheme document {suffix}",
        mime_type="application/pdf",
        content_hash=f"source-document-{suffix}",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name=f"Authority {suffix}",
        official_url=f"https://official-{suffix}.gov.in/",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Scheme {suffix}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"scheme-version-{suffix}",
        official_url=f"https://official-{suffix}.gov.in/scheme/",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path=f"manual.{suffix}_verification",
        operator=EligibilityRule.Operator.EXISTS,
        expected_value=True,
        mandatory=True,
        evidence_text=f"Verified official requirement {suffix}.",
        manually_verified=True,
    )
    return version, rule


def make_profile(*, owner: User, suffix: str) -> StartupProfile:
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=f"Startup {suffix}",
        stage=StartupProfile.Stage.MVP,
    )


def make_submission(
    *,
    profile: StartupProfile,
    version: SchemeVersion,
    rule: EligibilityRule,
    submitted_by: User,
    supersedes: EligibilityVerificationSubmission | None = None,
) -> EligibilityVerificationSubmission:
    return EligibilityVerificationSubmission.objects.create(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=submitted_by,
        supersedes=supersedes,
        claim_value=True,
        claim_text="The founder confirms this requirement.",
    )


def test_submission_rejects_rule_from_another_scheme_version():
    founder = make_user(username="rule-version-founder")
    profile = make_profile(owner=founder, suffix="rule-version")
    version_one, rule_one = make_scheme_context(suffix="one")
    version_two, _rule_two = make_scheme_context(suffix="two")

    with pytest.raises(ValidationError):
        make_submission(
            profile=profile,
            version=version_two,
            rule=rule_one,
            submitted_by=founder,
        )

    assert version_one.id == rule_one.scheme_version_id
    assert EligibilityVerificationSubmission.objects.count() == 0


def test_submission_rejects_invalid_supersession_context():
    founder = make_user(username="supersession-founder")
    other_founder = make_user(username="other-supersession-founder")
    profile = make_profile(owner=founder, suffix="primary")
    other_profile = make_profile(
        owner=other_founder,
        suffix="secondary",
    )
    version, rule = make_scheme_context(suffix="supersession")

    original = make_submission(
        profile=profile,
        version=version,
        rule=rule,
        submitted_by=founder,
    )

    with pytest.raises(ValidationError):
        make_submission(
            profile=other_profile,
            version=version,
            rule=rule,
            submitted_by=other_founder,
            supersedes=original,
        )

    second_rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="manual.second_requirement",
        operator=EligibilityRule.Operator.EXISTS,
        expected_value=True,
        mandatory=True,
        evidence_text="A second official manual requirement.",
        manually_verified=True,
    )

    with pytest.raises(ValidationError):
        make_submission(
            profile=profile,
            version=version,
            rule=second_rule,
            submitted_by=founder,
            supersedes=original,
        )


def test_only_one_current_submission_exists_per_profile_and_rule():
    founder = make_user(username="current-founder")
    profile = make_profile(owner=founder, suffix="current")
    version, rule = make_scheme_context(suffix="current")

    make_submission(
        profile=profile,
        version=version,
        rule=rule,
        submitted_by=founder,
    )

    with pytest.raises(ValidationError):
        make_submission(
            profile=profile,
            version=version,
            rule=rule,
            submitted_by=founder,
        )

    assert (
        EligibilityVerificationSubmission.objects.filter(
            startup_profile=profile,
            eligibility_rule=rule,
            is_current=True,
        ).count()
        == 1
    )


def test_decision_validates_outcome_value_and_dates():
    founder = make_user(username="decision-founder")
    reviewer = make_user(
        username="decision-reviewer",
        role=User.Role.REVIEWER,
    )
    profile = make_profile(owner=founder, suffix="decision")
    version, rule = make_scheme_context(suffix="decision")
    submission = make_submission(
        profile=profile,
        version=version,
        rule=rule,
        submitted_by=founder,
    )

    with pytest.raises(ValidationError):
        EligibilityVerificationDecision.objects.create(
            submission=submission,
            reviewed_by=reviewer,
            outcome=EligibilityVerificationDecision.Outcome.APPROVED,
            verified_value=None,
        )

    with pytest.raises(ValidationError):
        EligibilityVerificationDecision.objects.create(
            submission=submission,
            reviewed_by=reviewer,
            outcome=EligibilityVerificationDecision.Outcome.REJECTED,
            verified_value=True,
        )

    with pytest.raises(ValidationError):
        EligibilityVerificationDecision.objects.create(
            submission=submission,
            reviewed_by=reviewer,
            outcome=EligibilityVerificationDecision.Outcome.APPROVED,
            verified_value=True,
            valid_from=date(2026, 7, 23),
            expires_on=date(2026, 7, 22),
        )


def test_decision_is_immutable_for_instances_and_querysets():
    founder = make_user(username="immutable-founder")
    reviewer = make_user(
        username="immutable-reviewer",
        role=User.Role.REVIEWER,
    )
    profile = make_profile(owner=founder, suffix="immutable")
    version, rule = make_scheme_context(suffix="immutable")
    submission = make_submission(
        profile=profile,
        version=version,
        rule=rule,
        submitted_by=founder,
    )
    decision = EligibilityVerificationDecision.objects.create(
        submission=submission,
        reviewed_by=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        review_notes="Verified against submitted evidence.",
        submission_snapshot={"id": str(submission.id)},
        rule_snapshot={"id": str(rule.id)},
        evidence_snapshot=[],
    )

    decision.review_notes = "Attempted mutation."
    with pytest.raises(ValidationError):
        decision.save()

    with pytest.raises(ValidationError):
        decision.delete()

    with pytest.raises(ValidationError):
        EligibilityVerificationDecision.objects.filter(
            pk=decision.pk,
        ).update(review_notes="Bulk mutation.")

    with pytest.raises(ValidationError):
        EligibilityVerificationDecision.objects.filter(
            pk=decision.pk,
        ).delete()

    decision.refresh_from_db()
    assert decision.review_notes == ("Verified against submitted evidence.")


def test_duplicate_evidence_hash_is_rejected_for_one_submission():
    founder = make_user(username="evidence-founder")
    profile = make_profile(owner=founder, suffix="evidence")
    version, rule = make_scheme_context(suffix="evidence")
    submission = make_submission(
        profile=profile,
        version=version,
        rule=rule,
        submitted_by=founder,
    )

    EligibilityVerificationEvidence.objects.create(
        submission=submission,
        uploaded_by=founder,
        filename="proof-one.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        content_hash="a" * 64,
        storage_key="eligibility/test/proof-one.pdf",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        EligibilityVerificationEvidence.objects.create(
            submission=submission,
            uploaded_by=founder,
            filename="proof-two.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            content_hash="a" * 64,
            storage_key="eligibility/test/proof-two.pdf",
        )
