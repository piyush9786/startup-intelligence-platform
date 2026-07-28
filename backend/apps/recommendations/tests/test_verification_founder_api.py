from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.recommendations.models import (
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


def make_user(username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=User.Role.FOUNDER,
    )


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_context(*, suffix: str):
    founder = make_user(f"founder-{suffix}")
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name=f"Founder API Startup {suffix}",
        stage=StartupProfile.Stage.MVP,
    )
    source = Source.objects.create(
        name=f"Founder API source {suffix}",
        official_domain=f"founder-{suffix}.gov.in",
        listing_url=f"https://founder-{suffix}.gov.in/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=(f"https://founder-{suffix}.gov.in/scheme.pdf"),
        mime_type="application/pdf",
        content_hash=f"founder-api-document-{suffix}",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name=f"Founder API authority {suffix}",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Founder API scheme {suffix}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"founder-api-version-{suffix}",
        official_url=(f"https://founder-{suffix}.gov.in/scheme/"),
        application_status=(SchemeVersion.ApplicationStatus.OPEN),
        verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
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
    scheme.current_version = version
    scheme.save(update_fields=["current_version"])

    return (
        founder,
        profile,
        scheme,
        manual_rule,
        profile_rule,
    )


def test_owner_lists_manual_gate_status():
    founder, profile, scheme, manual_rule, _ = make_context(
        suffix="list",
    )
    client = authenticated_client(founder)

    response = client.get(
        reverse("eligibility-verification-gate-list"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "as_of_date": "2026-07-23",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["gate_count"] == 1
    assert response.data["unresolved_count"] == 1
    assert response.data["gates"][0]["eligibility_rule_id"] == str(manual_rule.id)
    assert response.data["gates"][0]["status"] == ("not_submitted")
    assert response.data["gates"][0]["resolved"] is False


def test_owner_creates_submission_and_gate_becomes_pending():
    founder, profile, scheme, manual_rule, _ = make_context(
        suffix="submit",
    )
    client = authenticated_client(founder)

    create_response = client.post(
        reverse("eligibility-verification-submission-create"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "eligibility_rule_id": str(manual_rule.id),
            "claim_value": True,
            "claim_text": "Endorsement has been obtained.",
        },
        format="json",
    )

    assert create_response.status_code == (status.HTTP_201_CREATED)
    assert create_response.data["is_current"] is True
    assert create_response.data["claim_value"] is True
    assert EligibilityVerificationSubmission.objects.count() == 1

    list_response = client.get(
        reverse("eligibility-verification-gate-list"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "as_of_date": date(2026, 7, 23).isoformat(),
        },
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["gates"][0]["status"] == ("pending")
    assert list_response.data["gates"][0]["submission"]["id"] == create_response.data["id"]


def test_owner_uploads_submission_evidence(monkeypatch):
    founder, profile, scheme, manual_rule, _ = make_context(
        suffix="upload",
    )
    client = authenticated_client(founder)

    submission_response = client.post(
        reverse("eligibility-verification-submission-create"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "eligibility_rule_id": str(manual_rule.id),
            "claim_value": True,
        },
        format="json",
    )
    submission_id = submission_response.data["id"]

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        lambda **kwargs: kwargs["object_key"],
    )

    response = client.post(
        reverse(
            "eligibility-verification-evidence-upload",
            kwargs={"submission_id": submission_id},
        ),
        {
            "file": SimpleUploadedFile(
                "endorsement.pdf",
                b"%PDF-1.7 endorsement evidence",
                content_type="application/pdf",
            ),
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["filename"] == "endorsement.pdf"
    assert response.data["mime_type"] == "application/pdf"
    assert response.data["size_bytes"] == len(b"%PDF-1.7 endorsement evidence")
    assert EligibilityVerificationEvidence.objects.count() == 1


def test_evidence_upload_rejects_spoofed_file_type(monkeypatch):
    founder, profile, scheme, manual_rule, _ = make_context(suffix="spoofed")
    client = authenticated_client(founder)
    submission_response = client.post(
        reverse("eligibility-verification-submission-create"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "eligibility_rule_id": str(manual_rule.id),
            "claim_value": True,
        },
        format="json",
    )
    upload_called = False

    def fake_upload(**kwargs):
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        fake_upload,
    )
    response = client.post(
        reverse(
            "eligibility-verification-evidence-upload",
            kwargs={"submission_id": submission_response.data["id"]},
        ),
        {
            "file": SimpleUploadedFile(
                "not-really.pdf",
                b"<script>not a PDF</script>",
                content_type="application/pdf",
            ),
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert upload_called is False


def test_other_founder_cannot_access_private_verification():
    founder, profile, scheme, manual_rule, _ = make_context(
        suffix="private",
    )
    other = make_user("other-private-founder")
    client = authenticated_client(other)

    list_response = client.get(
        reverse("eligibility-verification-gate-list"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
        },
    )
    create_response = client.post(
        reverse("eligibility-verification-submission-create"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "eligibility_rule_id": str(manual_rule.id),
            "claim_value": True,
        },
        format="json",
    )

    assert list_response.status_code == (status.HTTP_404_NOT_FOUND)
    assert create_response.status_code == (status.HTTP_404_NOT_FOUND)
    assert EligibilityVerificationSubmission.objects.count() == 0
    assert founder != other


def test_non_manual_rule_rejects_verification_submission():
    founder, profile, scheme, _, profile_rule = make_context(
        suffix="non-manual",
    )
    client = authenticated_client(founder)

    response = client.post(
        reverse("eligibility-verification-submission-create"),
        {
            "startup_profile_id": str(profile.id),
            "scheme_id": str(scheme.id),
            "eligibility_rule_id": str(profile_rule.id),
            "claim_value": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "eligibility_rule" in response.data
    assert EligibilityVerificationSubmission.objects.count() == 0
