from datetime import date
from hashlib import sha256

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
    EligibilityVerificationEvidence,
)
from apps.recommendations.services.verification import (
    add_verification_evidence,
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
) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
    )


def make_context(*, suffix: str):
    source = Source.objects.create(
        name=f"Evidence source {suffix}",
        official_domain=f"evidence-{suffix}.gov.in",
        listing_url=f"https://evidence-{suffix}.gov.in/schemes/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://evidence-{suffix}.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash=f"evidence-document-{suffix}",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name=f"Evidence authority {suffix}",
    )
    scheme = Scheme.objects.create(
        canonical_name=f"Evidence scheme {suffix}",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=f"evidence-version-{suffix}",
        official_url=f"https://evidence-{suffix}.gov.in/scheme/",
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    rule = EligibilityRule.objects.create(
        scheme_version=version,
        field_path=f"manual.evidence_{suffix}",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        mandatory=True,
        evidence_text="Official evidence is required.",
        manually_verified=True,
    )
    return version, rule


def make_submission(*, founder: User, suffix: str):
    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name=f"Evidence Startup {suffix}",
        stage=StartupProfile.Stage.MVP,
    )
    version, rule = make_context(suffix=suffix)
    submission = create_verification_submission(
        startup_profile=profile,
        scheme_version=version,
        eligibility_rule=rule,
        submitted_by=founder,
        claim_value=True,
        claim_text="The required evidence is attached.",
    )
    return submission


def test_owner_can_upload_evidence_metadata(monkeypatch):
    founder = make_user("evidence-upload-founder")
    submission = make_submission(
        founder=founder,
        suffix="upload",
    )
    content = b"verified evidence content"
    uploaded = {}

    def fake_upload_stream(**kwargs):
        uploaded.update(kwargs)
        return kwargs["object_key"]

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        fake_upload_stream,
    )

    evidence = add_verification_evidence(
        submission=submission,
        uploaded_by=founder,
        uploaded_file=SimpleUploadedFile(
            "../../proof.pdf",
            content,
            content_type="application/pdf",
        ),
    )

    assert evidence.filename == "proof.pdf"
    assert evidence.mime_type == "application/pdf"
    assert evidence.size_bytes == len(content)
    assert evidence.content_hash == sha256(content).hexdigest()
    assert evidence.storage_key.startswith(
        f"eligibility/{submission.startup_profile_id}/{submission.id}/"
    )
    assert uploaded["length"] == len(content)
    assert uploaded["stream"].read() == content
    assert uploaded["content_type"] == "application/pdf"
    assert uploaded["bucket_name"] == ("startup-eligibility-evidence")


def test_non_owner_cannot_upload_evidence(monkeypatch):
    founder = make_user("evidence-owner")
    outsider = make_user("evidence-outsider")
    submission = make_submission(
        founder=founder,
        suffix="ownership",
    )
    upload_called = False

    def fake_upload_stream(**kwargs):
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        fake_upload_stream,
    )

    with pytest.raises(ValidationError):
        add_verification_evidence(
            submission=submission,
            uploaded_by=outsider,
            uploaded_file=SimpleUploadedFile(
                "proof.pdf",
                b"private evidence",
                content_type="application/pdf",
            ),
        )

    assert upload_called is False
    assert EligibilityVerificationEvidence.objects.count() == 0


def test_reviewed_submission_rejects_additional_evidence(
    monkeypatch,
):
    founder = make_user("frozen-evidence-founder")
    reviewer = make_user(
        "frozen-evidence-reviewer",
        role=User.Role.REVIEWER,
    )
    submission = make_submission(
        founder=founder,
        suffix="frozen",
    )

    review_verification_submission(
        submission=submission,
        reviewer=reviewer,
        outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        verified_value=True,
        valid_from=date(2026, 7, 23),
    )

    upload_called = False

    def fake_upload_stream(**kwargs):
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        fake_upload_stream,
    )

    with pytest.raises(ValidationError):
        add_verification_evidence(
            submission=submission,
            uploaded_by=founder,
            uploaded_file=SimpleUploadedFile(
                "late-proof.pdf",
                b"late evidence",
                content_type="application/pdf",
            ),
        )

    assert upload_called is False


def test_database_failure_removes_uploaded_object(monkeypatch):
    founder = make_user("cleanup-evidence-founder")
    submission = make_submission(
        founder=founder,
        suffix="cleanup",
    )
    removed = []

    monkeypatch.setattr(
        "apps.recommendations.services.verification.upload_stream",
        lambda **kwargs: kwargs["object_key"],
    )

    monkeypatch.setattr(
        "apps.recommendations.services.verification.delete_object",
        lambda object_key, **kwargs: removed.append((object_key, kwargs["bucket_name"])),
    )

    def fail_save(self, *args, **kwargs):
        raise RuntimeError("Simulated database failure.")

    monkeypatch.setattr(
        EligibilityVerificationEvidence,
        "save",
        fail_save,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated database failure",
    ):
        add_verification_evidence(
            submission=submission,
            uploaded_by=founder,
            uploaded_file=SimpleUploadedFile(
                "cleanup.pdf",
                b"cleanup evidence",
                content_type="application/pdf",
            ),
        )

    assert len(removed) == 1
    assert removed[0][0].startswith(f"eligibility/{submission.startup_profile_id}/{submission.id}/")
    assert removed[0][1] == "startup-eligibility-evidence"
    assert EligibilityVerificationEvidence.objects.count() == 0
