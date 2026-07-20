import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.documents.models import DocumentExtraction
from apps.knowledge.models import (
    CandidateResolution,
    KnowledgeExtractionRun,
    SchemeCandidate,
)
from apps.knowledge.services.resolution import (
    resolve_candidate,
)
from apps.schemes.models import Authority
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


def make_candidate(
    *,
    key: str,
    title: str,
) -> SchemeCandidate:
    stable_key = hashlib.sha256(key.encode("utf-8")).hexdigest()

    source = Source.objects.create(
        name=f"Source {key}",
        official_domain=f"{key}.example.gov.in",
        listing_url=(f"https://{key}.example.gov.in"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_AUTHORITY),
    )

    document = SourceDocument.objects.create(
        source=source,
        source_url=(f"https://{key}.example.gov.in/document.pdf"),
        content_hash=stable_key,
        retrieved_at=timezone.now(),
    )

    extraction = DocumentExtraction.objects.create(
        source_document=document,
        extractor_version="test",
        status=DocumentExtraction.Status.SUCCEEDED,
    )

    run = KnowledgeExtractionRun.objects.create(
        extraction=extraction,
        extractor_version="v4",
        status=(KnowledgeExtractionRun.Status.SUCCEEDED),
    )

    return SchemeCandidate.objects.create(
        run=run,
        stable_key=stable_key,
        title=title,
        official_url=(f"https://{key}.example.gov.in/scheme"),
        confidence=90,
    )


@pytest.fixture
def reviewer():
    user_model = get_user_model()

    return user_model.objects.create_user(
        username="reviewer",
        email="reviewer@example.com",
        password="test-password",
        role=user_model.Role.REVIEWER,
    )


@pytest.fixture
def authority():
    return Authority.objects.create(
        name=("Department for Promotion of Industry and Internal Trade"),
    )


def test_canonical_resolution_approves_candidate(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="canonical",
        title="Startup Seed Fund Scheme",
    )

    resolution = resolve_candidate(
        candidate=candidate,
        classification=(CandidateResolution.Classification.CANONICAL),
        reviewer=reviewer,
        canonical_title=("Startup India Seed Fund Scheme"),
        resolved_authority=authority,
        review_notes=("Reviewed against official source."),
    )

    candidate.refresh_from_db()

    assert resolution.resolved_authority == authority
    assert resolution.resolved_by == reviewer
    assert resolution.resolved_at is not None
    assert candidate.review_status == SchemeCandidate.ReviewStatus.APPROVED


def test_rejected_resolution_rejects_candidate(
    reviewer,
):
    candidate = make_candidate(
        key="rejected",
        title="Scheme Name & Nodal",
    )

    resolution = resolve_candidate(
        candidate=candidate,
        classification=(CandidateResolution.Classification.REJECTED),
        reviewer=reviewer,
        review_notes="Table header extraction.",
    )

    candidate.refresh_from_db()

    assert resolution.classification == "rejected"
    assert candidate.review_status == SchemeCandidate.ReviewStatus.REJECTED


def test_supporting_resolution_requires_canonical_primary(
    reviewer,
    authority,
):
    primary = make_candidate(
        key="primary",
        title="DPIIT Recognition",
    )
    supporting = make_candidate(
        key="supporting",
        title="Benefits for a Recognised Startup",
    )

    resolve_candidate(
        candidate=primary,
        classification=(CandidateResolution.Classification.CANONICAL),
        reviewer=reviewer,
        canonical_title="DPIIT Startup Recognition",
        resolved_authority=authority,
    )

    resolution = resolve_candidate(
        candidate=supporting,
        classification=(CandidateResolution.Classification.SUPPORTING),
        reviewer=reviewer,
        canonical_title="DPIIT Startup Recognition",
        resolved_authority=authority,
        primary_candidate=primary,
    )

    supporting.refresh_from_db()

    assert resolution.primary_candidate == primary
    assert supporting.review_status == SchemeCandidate.ReviewStatus.APPROVED


def test_duplicate_requires_primary_candidate(
    reviewer,
):
    candidate = make_candidate(
        key="duplicate",
        title="Duplicate candidate",
    )

    with pytest.raises(ValidationError):
        resolve_candidate(
            candidate=candidate,
            classification=(CandidateResolution.Classification.DUPLICATE),
            reviewer=reviewer,
        )


def test_published_candidate_cannot_be_reresolved(
    reviewer,
):
    candidate = make_candidate(
        key="published",
        title="Published candidate",
    )

    candidate.review_status = SchemeCandidate.ReviewStatus.PUBLISHED
    candidate.save(
        update_fields=[
            "review_status",
            "updated_at",
        ]
    )

    with pytest.raises(ValidationError):
        resolve_candidate(
            candidate=candidate,
            classification=(CandidateResolution.Classification.REJECTED),
            reviewer=reviewer,
        )
