import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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
    PublishedEvidence,
    RequiredDocumentCandidate,
    SchemeCandidate,
)
from apps.knowledge.services.curation import (
    curate_candidate,
    review_structured_item,
)
from apps.knowledge.services.publication import publish_candidate
from apps.knowledge.services.resolution import resolve_candidate
from apps.schemes.models import (
    Authority,
    EligibilityRule,
    Scheme,
    SchemeVersion,
)
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


def make_candidate(
    *,
    key: str,
    title: str,
    summary: str = "Canonical summary.",
) -> SchemeCandidate:
    stable_key = hashlib.sha256(key.encode("utf-8")).hexdigest()

    source = Source.objects.create(
        name=f"Source {key}",
        official_domain=f"{key}.example.gov.in",
        listing_url=f"https://{key}.example.gov.in",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url=f"https://{key}.example.gov.in/document.pdf",
        content_hash=stable_key,
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
        heading=title,
        page_number=1,
        text=(f"{title}\nEligibility\nDPIIT recognised startups may apply."),
        text_hash=stable_key,
    )
    run = KnowledgeExtractionRun.objects.create(
        extraction=extraction,
        extractor_version="v4",
        status=KnowledgeExtractionRun.Status.SUCCEEDED,
    )
    candidate = SchemeCandidate.objects.create(
        run=run,
        stable_key=stable_key,
        title=title,
        kind=SchemeCandidate.Kind.FUND,
        summary=summary,
        eligibility_text="DPIIT recognised startups may apply.",
        benefits_text="Grant and seed support.",
        application_text="Apply through the official portal.",
        official_url=f"https://{key}.example.gov.in/scheme",
        application_url=f"https://{key}.example.gov.in/apply",
        confidence=90,
    )
    CandidateEvidence.objects.create(
        candidate=candidate,
        chunk=chunk,
        evidence_type=CandidateEvidence.EvidenceType.GENERAL,
        quote=chunk.text,
        page_number=1,
    )
    return candidate


@pytest.fixture
def reviewer():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="publication-reviewer",
        email="publication-reviewer@example.com",
        password="test-password",
        role=user_model.Role.REVIEWER,
    )


@pytest.fixture
def founder():
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="publication-founder",
        email="publication-founder@example.com",
        password="test-password",
        role=user_model.Role.FOUNDER,
    )


@pytest.fixture
def authority():
    return Authority.objects.create(
        name=("Department for Promotion of Industry and Internal Trade"),
    )


def resolve_as_canonical(
    *,
    candidate,
    reviewer,
    authority,
    canonical_title="Startup India Seed Fund Scheme",
):
    resolution = resolve_candidate(
        candidate=candidate,
        classification=CandidateResolution.Classification.CANONICAL,
        reviewer=reviewer,
        canonical_title=canonical_title,
        resolved_authority=authority,
        review_notes="Reviewed against official source.",
    )

    curate_candidate(
        candidate=candidate,
        status=CandidateCuration.ReviewStatus.APPROVED,
        reviewer=reviewer,
        canonical_summary=candidate.summary,
        canonical_objective=candidate.objective_text,
        canonical_eligibility_text=(candidate.eligibility_text),
        official_url=candidate.official_url,
        application_url=candidate.application_url,
        review_notes="Reviewed for canonical publication.",
    )

    return resolution


def test_canonical_publication_is_idempotent(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="publication-primary",
        title="Startup Seed Fund Scheme",
    )
    rule = EligibilityRuleCandidate.objects.create(
        candidate=candidate,
        field_name="dpiit_recognized",
        operator="eq",
        value=True,
        human_text="DPIIT recognised startups may apply.",
        confidence=95,
        review_status=EligibilityRuleCandidate.ReviewStatus.APPROVED,
    )
    resolve_as_canonical(
        candidate=candidate,
        reviewer=reviewer,
        authority=authority,
    )

    first = publish_candidate(
        candidate=candidate,
        publisher=reviewer,
    )
    second = publish_candidate(
        candidate=candidate,
        publisher=reviewer,
    )

    candidate.refresh_from_db()
    first.scheme.refresh_from_db()

    assert first.status == "version_created"
    assert second.status == "unchanged"
    assert first.scheme_version.version_number == 1
    assert first.scheme.lifecycle_status == Scheme.LifecycleStatus.ACTIVE
    assert first.scheme.current_version == first.scheme_version
    assert candidate.review_status == SchemeCandidate.ReviewStatus.PUBLISHED
    assert first.publication.role == CandidatePublication.Role.PRIMARY
    assert (
        PublishedEvidence.objects.filter(
            publication=first.publication,
        ).count()
        == 1
    )
    assert EligibilityRule.objects.filter(
        scheme_version=first.scheme_version,
        field_path=rule.field_name,
        operator=EligibilityRule.Operator.EQUALS,
        manually_verified=True,
    ).exists()
    assert Scheme.objects.count() == 1
    assert SchemeVersion.objects.count() == 1
    assert CandidatePublication.objects.count() == 1


def test_draft_rule_blocks_canonical_publication(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="publication-draft-rule",
        title="Draft Rule Scheme",
    )
    EligibilityRuleCandidate.objects.create(
        candidate=candidate,
        field_name="dpiit_recognized",
        operator="eq",
        value=True,
        human_text="Draft rule.",
        confidence=70,
    )
    resolve_as_canonical(
        candidate=candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title="Draft Rule Scheme",
    )

    with pytest.raises(ValidationError):
        publish_candidate(
            candidate=candidate,
            publisher=reviewer,
        )

    assert SchemeVersion.objects.count() == 0
    assert CandidatePublication.objects.count() == 0


def test_supporting_candidate_uses_primary_version(
    reviewer,
    authority,
):
    primary = make_candidate(
        key="publication-support-primary",
        title="DPIIT Startup Recognition",
    )
    supporting = make_candidate(
        key="publication-supporting",
        title="Benefits for a Recognised Startup",
    )
    canonical_title = "DPIIT Startup Recognition"

    resolve_as_canonical(
        candidate=primary,
        reviewer=reviewer,
        authority=authority,
        canonical_title=canonical_title,
    )
    primary_result = publish_candidate(
        candidate=primary,
        publisher=reviewer,
    )

    resolve_candidate(
        candidate=supporting,
        classification=CandidateResolution.Classification.SUPPORTING,
        reviewer=reviewer,
        canonical_title=canonical_title,
        resolved_authority=authority,
        primary_candidate=primary,
    )
    supporting_result = publish_candidate(
        candidate=supporting,
        publisher=reviewer,
    )

    supporting.refresh_from_db()

    assert supporting_result.status == "supporting_published"
    assert supporting_result.scheme_version == primary_result.scheme_version
    assert supporting_result.publication.role == CandidatePublication.Role.SUPPORTING
    assert supporting.review_status == SchemeCandidate.ReviewStatus.PUBLISHED
    assert Scheme.objects.count() == 1
    assert SchemeVersion.objects.count() == 1


def test_changed_payload_creates_next_version(
    reviewer,
    authority,
):
    first_candidate = make_candidate(
        key="publication-version-one",
        title="Versioned Scheme",
        summary="First published content.",
    )
    second_candidate = make_candidate(
        key="publication-version-two",
        title="Versioned Scheme",
        summary="Second published content.",
    )
    canonical_title = "Versioned Scheme"

    resolve_as_canonical(
        candidate=first_candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title=canonical_title,
    )
    first = publish_candidate(
        candidate=first_candidate,
        publisher=reviewer,
    )

    resolve_as_canonical(
        candidate=second_candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title=canonical_title,
    )
    second = publish_candidate(
        candidate=second_candidate,
        publisher=reviewer,
    )

    second.scheme.refresh_from_db()

    assert first.scheme == second.scheme
    assert first.scheme_version.version_number == 1
    assert second.scheme_version.version_number == 2
    assert second.created_version is True
    assert second.scheme.current_version == second.scheme_version
    assert SchemeVersion.objects.count() == 2


def test_founder_cannot_publish(
    reviewer,
    founder,
    authority,
):
    candidate = make_candidate(
        key="publication-unauthorized",
        title="Restricted Publication",
    )
    resolve_as_canonical(
        candidate=candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title="Restricted Publication",
    )

    with pytest.raises(ValidationError):
        publish_candidate(
            candidate=candidate,
            publisher=founder,
        )


def test_missing_curation_blocks_canonical_publication(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="publication-no-curation",
        title="Uncurated Scheme",
    )

    resolve_candidate(
        candidate=candidate,
        classification=(CandidateResolution.Classification.CANONICAL),
        reviewer=reviewer,
        canonical_title="Uncurated Scheme",
        resolved_authority=authority,
    )

    with pytest.raises(
        ValidationError,
        match="requires candidate curation",
    ):
        publish_candidate(
            candidate=candidate,
            publisher=reviewer,
        )


def test_draft_structured_item_blocks_publication(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="publication-draft-benefit",
        title="Draft Benefit Scheme",
    )

    BenefitCandidate.objects.create(
        candidate=candidate,
        description="Unreviewed benefit.",
        confidence=80,
    )

    resolve_as_canonical(
        candidate=candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title=("Draft Benefit Scheme"),
    )

    with pytest.raises(
        ValidationError,
        match="benefit",
    ):
        publish_candidate(
            candidate=candidate,
            publisher=reviewer,
        )


def test_publication_uses_curated_and_approved_content(
    reviewer,
    authority,
):
    candidate = make_candidate(
        key="publication-curated-content",
        title="Curated Scheme",
        summary="Raw extraction summary.",
    )

    approved_benefit = BenefitCandidate.objects.create(
        candidate=candidate,
        description="Approved benefit.",
        confidence=90,
    )
    rejected_benefit = BenefitCandidate.objects.create(
        candidate=candidate,
        description="Rejected fragment.",
        confidence=40,
    )

    approved_document = RequiredDocumentCandidate.objects.create(
        candidate=candidate,
        name="Approved document",
        description=("Reviewed requirement."),
        mandatory=True,
        confidence=90,
    )
    rejected_document = RequiredDocumentCandidate.objects.create(
        candidate=candidate,
        name="Rejected document",
        confidence=30,
    )

    approved_step = ApplicationStepCandidate.objects.create(
        candidate=candidate,
        step_number=1,
        instruction=("Use the reviewed portal."),
        url=("https://curated.example.gov.in/apply"),
        confidence=90,
    )
    rejected_step = ApplicationStepCandidate.objects.create(
        candidate=candidate,
        step_number=2,
        instruction=("Broken extracted fragment."),
        confidence=30,
    )

    for item in (
        approved_benefit,
        approved_document,
        approved_step,
    ):
        review_structured_item(
            item=item,
            status=(item.ReviewStatus.APPROVED),
            reviewer=reviewer,
        )

    for item in (
        rejected_benefit,
        rejected_document,
        rejected_step,
    ):
        review_structured_item(
            item=item,
            status=(item.ReviewStatus.REJECTED),
            reviewer=reviewer,
        )

    resolve_as_canonical(
        candidate=candidate,
        reviewer=reviewer,
        authority=authority,
        canonical_title="Curated Scheme",
    )

    curate_candidate(
        candidate=candidate,
        status=(CandidateCuration.ReviewStatus.APPROVED),
        reviewer=reviewer,
        canonical_summary=("Reviewed canonical summary."),
        canonical_objective=("Reviewed canonical objective."),
        canonical_eligibility_text=("Reviewed eligibility statement."),
        official_url=("https://curated.example.gov.in/scheme"),
        application_url=("https://curated.example.gov.in/apply"),
    )

    result = publish_candidate(
        candidate=candidate,
        publisher=reviewer,
    )

    version = result.scheme_version

    assert version.description == "Reviewed canonical summary."
    assert version.objective == "Reviewed canonical objective."
    assert version.official_url == ("https://curated.example.gov.in/scheme")
    assert version.application_url == ("https://curated.example.gov.in/apply")
    assert version.restrictions == ["Reviewed eligibility statement."]
    assert [row["description"] for row in version.benefits] == ["Approved benefit."]
    assert [row["name"] for row in version.required_documents] == ["Approved document"]
    assert [row["instruction"] for row in version.application_steps] == ["Use the reviewed portal."]
