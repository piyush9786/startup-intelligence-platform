import hashlib
import json
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.knowledge.models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateCuration,
    CandidateEvidence,
    CandidatePublication,
    CandidateResolution,
    EligibilityRuleCandidate,
    KnowledgeExtractionRun,
    RequiredDocumentCandidate,
    SchemeCandidate,
)
from apps.schemes.models import Authority, AuthorityAlias, Scheme
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviewer():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="pilot-reviewer",
        email="pilot-reviewer@example.com",
        password="test-password",
        role=user_model.Role.REVIEWER,
    )


def make_candidate():
    digest = hashlib.sha256(b"pilot-manifest").hexdigest()

    source = Source.objects.create(
        name="Pilot Source",
        official_domain="pilot.example.gov.in",
        listing_url="https://pilot.example.gov.in",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://pilot.example.gov.in/document.pdf",
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
        heading="Pilot Scheme",
        page_number=1,
        text="Pilot Scheme evidence.",
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
        title="Pilot Scheme",
        kind=SchemeCandidate.Kind.FUND,
        summary="Extracted summary.",
        official_url="https://pilot.example.gov.in/scheme",
        confidence=90,
    )
    CandidateEvidence.objects.create(
        candidate=candidate,
        chunk=chunk,
        evidence_type=CandidateEvidence.EvidenceType.GENERAL,
        quote=chunk.text,
        page_number=1,
    )
    rule = EligibilityRuleCandidate.objects.create(
        candidate=candidate,
        field_name="dpiit_recognized",
        operator="eq",
        value=True,
        unit="boolean",
        human_text="DPIIT recognised startups.",
        confidence=95,
    )
    benefit = BenefitCandidate.objects.create(
        candidate=candidate,
        description="Extracted benefit.",
        confidence=80,
    )
    document_item = RequiredDocumentCandidate.objects.create(
        candidate=candidate,
        name="Registration certificate",
        confidence=80,
    )
    step = ApplicationStepCandidate.objects.create(
        candidate=candidate,
        step_number=1,
        instruction="Use the application portal.",
        url="https://pilot.example.gov.in/apply",
        confidence=80,
    )

    return {
        "candidate": candidate,
        "source_document": document,
        "rule": rule,
        "benefit": benefit,
        "document": document_item,
        "step": step,
    }


def manifest_for(objects):
    candidate = objects["candidate"]
    source_document = objects["source_document"]

    return {
        "schema_version": 1,
        "manifest_key": "test-pilot-manifest",
        "extractor_version": "v4",
        "source_document": {
            "content_hash": source_document.content_hash,
            "source_name": "Pilot Source",
        },
        "authority": {
            "canonical_name": "Department for Pilot Testing",
            "authority_type": "central_government_department",
            "department": "Department for Pilot Testing",
            "aliases": [
                "DPT",
                "Department for Pilot Testing (DPT)",
            ],
        },
        "candidates": [
            {
                "pilot_key": "pilot",
                "candidate_id": str(candidate.id),
                "expected_title": candidate.title,
                "canonical_title": "Pilot Scheme",
                "classification": "canonical",
                "curation": {
                    "canonical_summary": "Reviewed summary.",
                    "canonical_objective": "Reviewed objective.",
                    "canonical_eligibility_text": "Reviewed eligibility.",
                    "official_url": "https://pilot.example.gov.in/scheme",
                    "application_url": "https://pilot.example.gov.in/apply",
                    "canonical_support_types": ["grant"],
                    "canonical_categories": ["pilot"],
                    "canonical_benefits": [
                        {
                            "type": "grant",
                            "description": "Reviewed benefit.",
                            "amount_min": None,
                            "amount_max": "1000000.00",
                            "currency": "INR",
                        }
                    ],
                    "canonical_required_documents": [],
                    "canonical_application_steps": [
                        {
                            "step_number": 1,
                            "instruction": "Use the reviewed portal.",
                            "url": "https://pilot.example.gov.in/apply",
                        }
                    ],
                },
                "eligibility_rules": {
                    "approve": [str(objects["rule"].id)],
                    "reject": [],
                },
                "structured_reviews": {
                    "benefits": {
                        "approve": [],
                        "reject": [str(objects["benefit"].id)],
                    },
                    "required_documents": {
                        "approve": [],
                        "reject": [str(objects["document"].id)],
                    },
                    "application_steps": {
                        "approve": [],
                        "reject": [str(objects["step"].id)],
                    },
                },
            }
        ],
    }


def write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_dry_run_does_not_mutate(reviewer, tmp_path):
    objects = make_candidate()
    path = write_manifest(tmp_path, manifest_for(objects))
    stdout = StringIO()

    call_command(
        "apply_pilot_manifest",
        manifest=str(path),
        reviewer_email=reviewer.email,
        stdout=stdout,
    )

    objects["candidate"].refresh_from_db()
    objects["rule"].refresh_from_db()
    objects["benefit"].refresh_from_db()

    assert "DRY RUN" in stdout.getvalue()
    assert Authority.objects.count() == 0
    assert AuthorityAlias.objects.count() == 0
    assert CandidateResolution.objects.count() == 0
    assert CandidateCuration.objects.count() == 0
    assert objects["candidate"].review_status == SchemeCandidate.ReviewStatus.NEEDS_REVIEW
    assert objects["rule"].review_status == EligibilityRuleCandidate.ReviewStatus.DRAFT
    assert objects["benefit"].review_status == BenefitCandidate.ReviewStatus.DRAFT


def test_apply_reviews_without_publication(reviewer, tmp_path):
    objects = make_candidate()
    path = write_manifest(tmp_path, manifest_for(objects))

    call_command(
        "apply_pilot_manifest",
        manifest=str(path),
        reviewer_email=reviewer.email,
        apply=True,
    )

    candidate = objects["candidate"]
    candidate.refresh_from_db()
    objects["rule"].refresh_from_db()
    objects["benefit"].refresh_from_db()
    objects["document"].refresh_from_db()
    objects["step"].refresh_from_db()

    authority = Authority.objects.get()
    resolution = candidate.resolution
    curation = candidate.curation

    assert authority.name == "Department for Pilot Testing"
    assert AuthorityAlias.objects.count() == 2
    assert resolution.classification == CandidateResolution.Classification.CANONICAL
    assert resolution.resolved_authority == authority
    assert curation.review_status == CandidateCuration.ReviewStatus.APPROVED
    assert curation.canonical_benefits[0]["description"] == "Reviewed benefit."
    assert objects["rule"].review_status == EligibilityRuleCandidate.ReviewStatus.APPROVED
    assert objects["benefit"].review_status == BenefitCandidate.ReviewStatus.REJECTED
    assert objects["document"].review_status == RequiredDocumentCandidate.ReviewStatus.REJECTED
    assert objects["step"].review_status == ApplicationStepCandidate.ReviewStatus.REJECTED
    assert candidate.review_status == SchemeCandidate.ReviewStatus.APPROVED
    assert Scheme.objects.count() == 0
    assert CandidatePublication.objects.count() == 0


def test_invalid_child_id_is_atomic(reviewer, tmp_path):
    objects = make_candidate()
    manifest = manifest_for(objects)
    manifest["candidates"][0]["eligibility_rules"]["approve"] = [str(uuid4())]
    path = write_manifest(tmp_path, manifest)

    with pytest.raises(CommandError, match="cover every rule"):
        call_command(
            "apply_pilot_manifest",
            manifest=str(path),
            reviewer_email=reviewer.email,
            apply=True,
        )

    assert Authority.objects.count() == 0
    assert CandidateResolution.objects.count() == 0
    assert CandidateCuration.objects.count() == 0


def test_apply_is_count_idempotent(reviewer, tmp_path):
    objects = make_candidate()
    path = write_manifest(tmp_path, manifest_for(objects))

    for _index in range(2):
        call_command(
            "apply_pilot_manifest",
            manifest=str(path),
            reviewer_email=reviewer.email,
            apply=True,
        )

    assert Authority.objects.count() == 1
    assert AuthorityAlias.objects.count() == 2
    assert CandidateResolution.objects.count() == 1
    assert CandidateCuration.objects.count() == 1
    assert Scheme.objects.count() == 0
    assert CandidatePublication.objects.count() == 0
