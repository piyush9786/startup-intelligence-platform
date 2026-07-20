import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.documents.models import DocumentExtraction
from apps.knowledge.models import (
    BenefitCandidate,
    CandidateCuration,
    EligibilityRuleCandidate,
    KnowledgeExtractionRun,
    SchemeCandidate,
)
from apps.knowledge.services.curation import (
    curate_candidate,
    review_eligibility_rule,
    review_structured_item,
)
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


def make_candidate(
    *,
    key: str,
) -> SchemeCandidate:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()

    source = Source.objects.create(
        name=f"Source {key}",
        official_domain=f"{key}.example.gov.in",
        listing_url=(f"https://{key}.example.gov.in"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_AUTHORITY),
    )

    document = SourceDocument.objects.create(
        source=source,
        source_url=(f"https://{key}.example.gov.in/document.pdf"),
        content_hash=digest,
        retrieved_at=timezone.now(),
    )

    extraction = DocumentExtraction.objects.create(
        source_document=document,
        extractor_version="test",
        status=(DocumentExtraction.Status.SUCCEEDED),
    )

    run = KnowledgeExtractionRun.objects.create(
        extraction=extraction,
        extractor_version="v4",
        status=(KnowledgeExtractionRun.Status.SUCCEEDED),
    )

    return SchemeCandidate.objects.create(
        run=run,
        stable_key=digest,
        title="Pilot Scheme",
        official_url=(f"https://{key}.example.gov.in/scheme"),
        confidence=90,
    )


@pytest.fixture
def reviewer():
    user_model = get_user_model()

    return user_model.objects.create_user(
        username="curation-reviewer",
        email="curation-reviewer@example.com",
        password="test-password",
        role=user_model.Role.REVIEWER,
    )


@pytest.fixture
def founder():
    user_model = get_user_model()

    return user_model.objects.create_user(
        username="curation-founder",
        email="curation-founder@example.com",
        password="test-password",
        role=user_model.Role.FOUNDER,
    )


def test_approved_curation_records_audit(
    reviewer,
):
    candidate = make_candidate(
        key="approved-curation",
    )

    curation = curate_candidate(
        candidate=candidate,
        status=(CandidateCuration.ReviewStatus.APPROVED),
        reviewer=reviewer,
        canonical_summary=("Reviewed canonical summary."),
        canonical_objective=("Reviewed canonical objective."),
        canonical_eligibility_text=("Reviewed eligibility."),
        official_url=("https://example.gov.in/scheme"),
        application_url=("https://example.gov.in/apply"),
    )

    assert curation.reviewed_by == reviewer
    assert curation.reviewed_at is not None


def test_founder_cannot_approve_curation(
    founder,
):
    candidate = make_candidate(
        key="founder-curation",
    )

    with pytest.raises(ValidationError):
        curate_candidate(
            candidate=candidate,
            status=(CandidateCuration.ReviewStatus.APPROVED),
            reviewer=founder,
            canonical_summary=("Reviewed canonical summary."),
            official_url=("https://example.gov.in/scheme"),
        )


def test_structured_item_review_records_audit(
    reviewer,
):
    candidate = make_candidate(
        key="benefit-review",
    )

    benefit = BenefitCandidate.objects.create(
        candidate=candidate,
        description="Up to INR 20 lakh.",
        confidence=90,
    )

    reviewed = review_structured_item(
        item=benefit,
        status=(BenefitCandidate.ReviewStatus.APPROVED),
        reviewer=reviewer,
        review_notes="Verified against source.",
    )

    assert reviewed.reviewed_by == reviewer
    assert reviewed.reviewed_at is not None
    assert reviewed.review_status == BenefitCandidate.ReviewStatus.APPROVED


def test_returning_item_to_draft_clears_audit(
    reviewer,
):
    candidate = make_candidate(
        key="benefit-draft",
    )

    benefit = BenefitCandidate.objects.create(
        candidate=candidate,
        description="Draft benefit.",
        confidence=70,
    )

    review_structured_item(
        item=benefit,
        status=(BenefitCandidate.ReviewStatus.REJECTED),
        reviewer=reviewer,
    )

    reviewed = review_structured_item(
        item=benefit,
        status=(BenefitCandidate.ReviewStatus.DRAFT),
        reviewer=None,
    )

    assert reviewed.reviewed_by is None
    assert reviewed.reviewed_at is None


def make_rule(
    *,
    candidate,
):
    return EligibilityRuleCandidate.objects.create(
        candidate=candidate,
        field_name="dpiit_recognized",
        operator="eq",
        value=True,
        unit="boolean",
        human_text=("DPIIT recognised startups."),
        confidence=95,
    )


def test_eligibility_rule_review_records_audit(
    reviewer,
):
    candidate = make_candidate(
        key="eligibility-review",
    )
    rule = make_rule(candidate=candidate)

    reviewed = review_eligibility_rule(
        rule=rule,
        status=(EligibilityRuleCandidate.ReviewStatus.APPROVED),
        reviewer=reviewer,
        review_notes=("Verified against official evidence."),
    )

    assert reviewed.reviewed_by == reviewer
    assert reviewed.reviewed_at is not None
    assert reviewed.review_status == (EligibilityRuleCandidate.ReviewStatus.APPROVED)


def test_founder_cannot_review_eligibility_rule(
    founder,
):
    candidate = make_candidate(
        key="eligibility-founder",
    )
    rule = make_rule(candidate=candidate)

    with pytest.raises(ValidationError):
        review_eligibility_rule(
            rule=rule,
            status=(EligibilityRuleCandidate.ReviewStatus.APPROVED),
            reviewer=founder,
        )


def test_returning_rule_to_draft_clears_audit(
    reviewer,
):
    candidate = make_candidate(
        key="eligibility-draft",
    )
    rule = make_rule(candidate=candidate)

    review_eligibility_rule(
        rule=rule,
        status=(EligibilityRuleCandidate.ReviewStatus.REJECTED),
        reviewer=reviewer,
    )

    reviewed = review_eligibility_rule(
        rule=rule,
        status=(EligibilityRuleCandidate.ReviewStatus.DRAFT),
        reviewer=None,
    )

    assert reviewed.reviewed_by is None
    assert reviewed.reviewed_at is None
