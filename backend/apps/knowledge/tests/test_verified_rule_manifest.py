import hashlib
import json
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.knowledge.models import (
    CandidateEvidence,
    CandidatePublication,
    KnowledgeExtractionRun,
    SchemeCandidate,
    VerifiedRuleRevision,
)
from apps.schemes.models import Authority, EligibilityRule, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviewer():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="rule-reviewer",
        email="rule-reviewer@example.com",
        password="test-password",
        role=user_model.Role.REVIEWER,
    )


def make_published_scheme(reviewer):
    digest = hashlib.sha256(b"verified-rule-manifest").hexdigest()
    source = Source.objects.create(
        name="Verified Rule Source",
        official_domain="verified-rules.example.gov.in",
        listing_url="https://verified-rules.example.gov.in",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://verified-rules.example.gov.in/source.pdf",
        content_hash=digest,
        retrieved_at=timezone.now(),
    )
    extraction = DocumentExtraction.objects.create(
        source_document=document,
        extractor_version="test",
        status=DocumentExtraction.Status.SUCCEEDED,
    )
    chunk = DocumentChunk.objects.create(
        extraction=extraction,
        chunk_index=0,
        page_number=1,
        text="Verified eligibility evidence.",
        text_hash=digest,
    )
    run = KnowledgeExtractionRun.objects.create(
        extraction=extraction,
        extractor_version="v4",
        status=KnowledgeExtractionRun.Status.SUCCEEDED,
    )
    candidate = SchemeCandidate.objects.create(
        run=run,
        stable_key=digest,
        title="Verified Rule Scheme",
        kind=SchemeCandidate.Kind.GRANT,
        review_status=SchemeCandidate.ReviewStatus.PUBLISHED,
        confidence=95,
    )
    CandidateEvidence.objects.create(
        candidate=candidate,
        chunk=chunk,
        evidence_type=CandidateEvidence.EvidenceType.ELIGIBILITY,
        quote=chunk.text,
        page_number=1,
    )

    authority = Authority.objects.create(name="Verified Rule Authority")
    scheme = Scheme.objects.create(
        canonical_name="Verified Rule Scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash=hashlib.sha256(b"base-version").hexdigest(),
        description="Reviewed description.",
        restrictions=["Reviewed eligibility text."],
        official_url="https://verified-rules.example.gov.in/scheme",
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        verified_at=timezone.now(),
        verified_by=reviewer,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version", "updated_at"])

    publication = CandidatePublication.objects.create(
        candidate=candidate,
        scheme=scheme,
        scheme_version=version,
        role=CandidatePublication.Role.PRIMARY,
        publication_hash=version.content_hash,
        published_by=reviewer,
        published_at=timezone.now(),
    )

    return {
        "candidate": candidate,
        "publication": publication,
        "scheme": scheme,
        "version": version,
    }


def manifest_for(objects):
    scheme = objects["scheme"]
    version = objects["version"]
    publication = objects["publication"]
    return {
        "schema_version": 1,
        "manifest_key": "test-verified-rules-v1",
        "revisions": [
            {
                "pilot_key": "test",
                "scheme_id": str(scheme.id),
                "source_publication_id": str(publication.id),
                "expected_current_version_id": str(version.id),
                "expected_current_version_number": 1,
                "expected_current_content_hash": version.content_hash,
                "rules": [
                    {
                        "rule_key": "startup_applicant",
                        "evaluation_mode": "executable",
                        "field_path": "eligible_entity_type",
                        "operator": "contains_any",
                        "expected_value": ["startup"],
                        "mandatory": True,
                        "evidence_text": "Startups may apply.",
                        "evidence_page": 1,
                    },
                    {
                        "rule_key": "incubator_check",
                        "evaluation_mode": "manual_verification",
                        "field_path": (
                            "manual_verification.incubator_association"
                        ),
                        "operator": "exists",
                        "expected_value": None,
                        "mandatory": True,
                        "evidence_text": (
                            "Incubator association must be verified."
                        ),
                        "evidence_page": 1,
                    },
                ],
            }
        ],
    }


def write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "verified-rules.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_dry_run_does_not_create_versions(reviewer, tmp_path):
    objects = make_published_scheme(reviewer)
    path = write_manifest(tmp_path, manifest_for(objects))
    stdout = StringIO()

    call_command(
        "apply_verified_rule_manifest",
        manifest=str(path),
        reviewer_email=reviewer.email,
        stdout=stdout,
    )

    objects["scheme"].refresh_from_db()
    assert "DRY RUN" in stdout.getvalue()
    assert objects["scheme"].current_version_id == objects["version"].id
    assert SchemeVersion.objects.count() == 1
    assert EligibilityRule.objects.count() == 0
    assert VerifiedRuleRevision.objects.count() == 0


def test_apply_creates_immutable_verified_version(reviewer, tmp_path):
    objects = make_published_scheme(reviewer)
    path = write_manifest(tmp_path, manifest_for(objects))

    call_command(
        "apply_verified_rule_manifest",
        manifest=str(path),
        reviewer_email=reviewer.email,
        apply=True,
    )

    objects["scheme"].refresh_from_db()
    revised = objects["scheme"].current_version
    audit = VerifiedRuleRevision.objects.get()

    assert revised.id != objects["version"].id
    assert revised.version_number == 2
    assert revised.verification_status == "verified"
    assert revised.description == objects["version"].description
    assert revised.restrictions == objects["version"].restrictions
    assert revised.eligibility_rules.count() == 2
    assert objects["version"].eligibility_rules.count() == 0
    assert audit.base_version == objects["version"]
    assert audit.revised_version == revised
    assert audit.source_publication == objects["publication"]
    assert audit.metadata["executable_rule_count"] == 1
    assert audit.metadata["manual_rule_count"] == 1

    rules = list(revised.eligibility_rules.order_by("field_path"))
    assert rules[0].field_path == "eligible_entity_type"
    assert rules[0].manually_verified is True
    assert rules[1].field_path == "manual_verification.incubator_association"
    assert rules[1].manually_verified is True


def test_apply_is_count_idempotent(reviewer, tmp_path):
    objects = make_published_scheme(reviewer)
    path = write_manifest(tmp_path, manifest_for(objects))

    for _index in range(2):
        call_command(
            "apply_verified_rule_manifest",
            manifest=str(path),
            reviewer_email=reviewer.email,
            apply=True,
        )

    assert SchemeVersion.objects.count() == 2
    assert EligibilityRule.objects.count() == 2
    assert VerifiedRuleRevision.objects.count() == 1


def test_base_content_mismatch_is_atomic(reviewer, tmp_path):
    objects = make_published_scheme(reviewer)
    manifest = manifest_for(objects)
    manifest["revisions"][0]["expected_current_content_hash"] = "0" * 64
    path = write_manifest(tmp_path, manifest)

    with pytest.raises(CommandError, match="content hash does not match"):
        call_command(
            "apply_verified_rule_manifest",
            manifest=str(path),
            reviewer_email=reviewer.email,
            apply=True,
        )

    assert SchemeVersion.objects.count() == 1
    assert EligibilityRule.objects.count() == 0
    assert VerifiedRuleRevision.objects.count() == 0


def test_manual_rule_requires_explicit_namespace(reviewer, tmp_path):
    objects = make_published_scheme(reviewer)
    manifest = manifest_for(objects)
    manifest["revisions"][0]["rules"][1][
        "field_path"
    ] = "incubator_association"
    path = write_manifest(tmp_path, manifest)

    with pytest.raises(CommandError, match="manual field must start"):
        call_command(
            "apply_verified_rule_manifest",
            manifest=str(path),
            reviewer_email=reviewer.email,
            apply=True,
        )
