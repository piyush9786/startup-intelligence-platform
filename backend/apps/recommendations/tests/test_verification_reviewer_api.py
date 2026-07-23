from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
    EligibilityVerificationEvidence,
)
from apps.recommendations.services.verification import (
    create_verification_submission,
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
    role: str,
) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
    )


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_context(*, suffix: str):
    founder = make_user(
        f"review-founder-{suffix}",
        role=User.Role.FOUNDER,
    )
    reviewer = make_user(
        f"reviewer-{suffix}",
        role=User.Role.REVIEWER,
    )
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name=f"Reviewer API Startup {suffix}",
        stage=StartupProfile.Stage.MVP,
    )
    source = Source.objects.create(
        name=f"Reviewer API source {suffix}",
        official_domain=f"reviewer-{suffix}.gov.in",
        listing_url=f"https://reviewer-{suffix}.gov.in/",
        authority_tier=(Source.AuthorityTier.OFFICIAL_PROGRAMME),
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=(f"https://reviewer-{suffix}.gov.in/scheme.pdf"),
        mime_type="application/pdf",
        content_hash=f"reviewer-api-document-{suffix}",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name=f"Reviewer API authority {suffix}",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Reviewer API scheme {suffix}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"reviewer-api-version-{suffix}",
        official_url=(f"https://reviewer-{suffix}.gov.in/scheme/"),
        application_status=(SchemeVersion.ApplicationStatus.OPEN),
        verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
    )
    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path="manual.incubator_endorsement",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="Incubator endorsement is required.",
        manually_verified=True,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version"])

    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
        claim_text="The endorsement has been obtained.",
    )

    return founder, reviewer, profile, submission


def test_reviewer_can_list_current_submission_queue():
    _founder, reviewer, profile, submission = make_context(
        suffix="queue",
    )
    evidence = EligibilityVerificationEvidence.objects.create(
        submission=submission,
        uploaded_by=submission.submitted_by,
        filename="endorsement.pdf",
        mime_type="application/pdf",
        size_bytes=128,
        content_hash="a" * 64,
        storage_key="eligibility/reviewer/endorsement.pdf",
    )
    client = authenticated_client(reviewer)

    response = client.get(
        reverse("eligibility-verification-reviewer-queue"),
        {"as_of_date": "2026-07-23"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    item = response.data["submissions"][0]
    assert item["id"] == str(submission.id)
    assert item["status"] == "pending"
    assert item["startup_profile_id"] == str(profile.id)
    assert item["evidence_count"] == 1
    assert item["evidence"][0]["id"] == str(evidence.id)
    assert "storage_key" not in item["evidence"][0]


def test_founder_cannot_access_reviewer_endpoints():
    founder, _reviewer, _profile, submission = make_context(
        suffix="forbidden",
    )
    client = authenticated_client(founder)

    queue_response = client.get(
        reverse("eligibility-verification-reviewer-queue"),
    )
    decision_response = client.post(
        reverse(
            "eligibility-verification-reviewer-decision-create",
            kwargs={"submission_id": submission.id},
        ),
        {
            "outcome": "approved",
            "verified_value": True,
        },
        format="json",
    )

    assert queue_response.status_code == (status.HTTP_403_FORBIDDEN)
    assert decision_response.status_code == (status.HTTP_403_FORBIDDEN)
    assert EligibilityVerificationDecision.objects.count() == 0


def test_reviewer_can_approve_submission():
    _founder, reviewer, _profile, submission = make_context(
        suffix="approve",
    )
    client = authenticated_client(reviewer)

    response = client.post(
        reverse(
            "eligibility-verification-reviewer-decision-create",
            kwargs={"submission_id": submission.id},
        ),
        {
            "outcome": "approved",
            "verified_value": True,
            "review_notes": "Evidence verified.",
            "valid_from": "2026-07-01",
            "expires_on": "2026-12-31",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["outcome"] == "approved"
    assert response.data["verified_value"] is True
    assert response.data["reviewed_by_id"] == str(reviewer.id)

    decision = EligibilityVerificationDecision.objects.get()
    assert decision.submission_snapshot["id"] == str(submission.id)
    assert decision.rule_snapshot["id"] == str(submission.eligibility_rule_id)

    queue_response = client.get(
        reverse("eligibility-verification-reviewer-queue"),
        {"as_of_date": "2026-07-23"},
    )

    assert queue_response.data["submissions"][0]["status"] == "approved"


def test_rejected_decision_cannot_include_verified_value():
    _founder, reviewer, _profile, submission = make_context(
        suffix="invalid-rejection",
    )
    client = authenticated_client(reviewer)

    response = client.post(
        reverse(
            "eligibility-verification-reviewer-decision-create",
            kwargs={"submission_id": submission.id},
        ),
        {
            "outcome": "rejected",
            "verified_value": True,
            "review_notes": "Invalid evidence.",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "verified_value" in response.data
    assert EligibilityVerificationDecision.objects.count() == 0


def test_admin_role_can_review_submission():
    _founder, _reviewer, _profile, submission = make_context(
        suffix="admin",
    )
    admin = make_user(
        "verification-admin",
        role=User.Role.ADMIN,
    )
    client = authenticated_client(admin)

    response = client.post(
        reverse(
            "eligibility-verification-reviewer-decision-create",
            kwargs={"submission_id": submission.id},
        ),
        {
            "outcome": "rejected",
            "review_notes": "Evidence was insufficient.",
            "valid_from": date(2026, 7, 23).isoformat(),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["outcome"] == "rejected"
    assert response.data["reviewed_by_id"] == str(admin.id)


def test_reviewer_can_download_evidence(monkeypatch):
    _founder, reviewer, _profile, submission = make_context(
        suffix="download",
    )
    evidence = EligibilityVerificationEvidence.objects.create(
        submission=submission,
        uploaded_by=submission.submitted_by,
        filename="verification-proof.pdf",
        mime_type="application/pdf",
        size_bytes=17,
        content_hash="b" * 64,
        storage_key="eligibility/reviewer/proof.pdf",
    )
    downloaded = b"reviewable content"

    monkeypatch.setattr(
        ("apps.recommendations.verification_reviewer_views.download_bytes"),
        lambda object_key, **kwargs: downloaded,
    )

    client = authenticated_client(reviewer)
    response = client.get(
        reverse(
            "eligibility-verification-reviewer-evidence-download",
            kwargs={"evidence_id": evidence.id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "application/pdf"
    assert "verification-proof.pdf" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == downloaded
