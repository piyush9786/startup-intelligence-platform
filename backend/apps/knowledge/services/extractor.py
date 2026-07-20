from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.discovery.models import DocumentQualityAssessment
from apps.documents.models import DocumentChunk, DocumentExtraction

from ..models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateEvidence,
    EligibilityRuleCandidate,
    KnowledgeExtractionRun,
    RequiredDocumentCandidate,
    SchemeCandidate,
)
from .parser import (
    CandidateBlock,
    detect_authority,
    detect_kind,
    extract_urls,
    parse_amounts,
    parse_rules,
    segment_candidates,
    split_block_sections,
    split_items,
    stable_candidate_key,
)


class KnowledgeExtractionError(RuntimeError):
    """Raised when an extraction cannot produce reviewable candidates."""


@dataclass(frozen=True)
class KnowledgeExtractionResult:
    run: KnowledgeExtractionRun
    created: bool
    unchanged: bool
    candidate_count: int


def _evidence_type(section: str) -> str:
    mapping = {
        "eligibility": CandidateEvidence.EvidenceType.ELIGIBILITY,
        "benefit": CandidateEvidence.EvidenceType.BENEFIT,
        "application": CandidateEvidence.EvidenceType.APPLICATION,
        "document": CandidateEvidence.EvidenceType.DOCUMENT,
        "objective": CandidateEvidence.EvidenceType.OBJECTIVE,
        "authority": CandidateEvidence.EvidenceType.AUTHORITY,
        "summary": CandidateEvidence.EvidenceType.SUMMARY,
    }
    return mapping.get(section, CandidateEvidence.EvidenceType.GENERAL)


def _section_payload(
    block: CandidateBlock,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[DocumentChunk]],
]:
    values, raw_evidence = split_block_sections(block)
    evidence: dict[str, list[DocumentChunk]] = {
        section: list(chunks) for section, chunks in raw_evidence.items()
    }
    return values, evidence


def _join(values: list[str], limit: int = 20000) -> str:
    output = "\n\n".join(value for value in values if value).strip()
    return output[:limit]


def _best_source_url(extraction: DocumentExtraction) -> str:
    document = extraction.source_document
    return document.final_url or document.source_url


def _candidate_confidence(block: CandidateBlock) -> Decimal:
    return min(Decimal("0.98"), Decimal("0.45") + Decimal(block.score) * Decimal("0.07"))


def _create_candidate(
    run: KnowledgeExtractionRun,
    extraction: DocumentExtraction,
    block: CandidateBlock,
) -> SchemeCandidate:
    values, evidence = _section_payload(block)
    eligibility_text = _join(values["eligibility"])
    benefits_text = _join(values["benefit"])
    application_text = _join(values["application"])
    documents_text = _join(values["document"])
    objective_text = _join(values["objective"])
    summary_text = _join(values["summary"], limit=5000)
    authority_text = _join(values["authority"], limit=5000)
    authority_name, ministry_name = detect_authority(f"{authority_text}\n{block.raw_text[:8000]}")
    amounts = parse_amounts(benefits_text or block.raw_text)
    amount_values = sorted({item.value for item in amounts})
    urls = extract_urls(application_text or block.raw_text)
    source_url = _best_source_url(extraction)
    application_url = urls[0] if urls else ""
    candidate = SchemeCandidate.objects.create(
        run=run,
        stable_key=stable_candidate_key(
            block.title,
            block.start_page,
            block.raw_text,
        ),
        title=block.title,
        kind=detect_kind(block.title, block.raw_text),
        authority_name=authority_name,
        ministry_name=ministry_name,
        summary=summary_text[:2000],
        objective_text=objective_text,
        eligibility_text=eligibility_text,
        benefits_text=benefits_text,
        application_text=application_text,
        required_documents_text=documents_text,
        official_url=source_url,
        application_url=application_url,
        financial_amount_min=amount_values[0] if amount_values else None,
        financial_amount_max=amount_values[-1] if amount_values else None,
        start_page=block.start_page,
        end_page=block.end_page,
        confidence=_candidate_confidence(block),
        review_status=SchemeCandidate.ReviewStatus.NEEDS_REVIEW,
        raw_text=block.raw_text,
        metadata={
            "candidate_score": block.score,
            "chunk_count": len(block.chunks),
            "source_extraction_id": str(extraction.id),
            "source_document_id": str(extraction.source_document_id),
        },
    )

    CandidateEvidence.objects.create(
        candidate=candidate,
        chunk=block.chunks[0],
        evidence_type=CandidateEvidence.EvidenceType.TITLE,
        quote=block.title,
        page_number=block.chunks[0].page_number,
    )
    for section, chunks in evidence.items():
        for chunk in chunks:
            CandidateEvidence.objects.get_or_create(
                candidate=candidate,
                chunk=chunk,
                evidence_type=_evidence_type(section),
                defaults={
                    "quote": chunk.text[:2000],
                    "page_number": chunk.page_number,
                    "metadata": {"heading": chunk.heading},
                },
            )

    chunk_by_section = {
        section: chunks[0] if chunks else None for section, chunks in evidence.items()
    }
    for rule in parse_rules(eligibility_text):
        EligibilityRuleCandidate.objects.create(
            candidate=candidate,
            source_chunk=chunk_by_section["eligibility"],
            field_name=rule.field_name,
            operator=rule.operator,
            value=rule.value,
            unit=rule.unit,
            human_text=rule.human_text,
            confidence=rule.confidence,
        )

    benefit_items = split_items(benefits_text)
    for item in benefit_items[:50]:
        item_amounts = parse_amounts(item)
        item_values = sorted({amount.value for amount in item_amounts})
        BenefitCandidate.objects.create(
            candidate=candidate,
            source_chunk=chunk_by_section["benefit"],
            description=item,
            amount_min=item_values[0] if item_values else None,
            amount_max=item_values[-1] if item_values else None,
            confidence=Decimal("0.70"),
        )

    for item in split_items(documents_text)[:50]:
        RequiredDocumentCandidate.objects.create(
            candidate=candidate,
            source_chunk=chunk_by_section["document"],
            name=item[:500],
            description=item if len(item) > 500 else "",
            confidence=Decimal("0.72"),
        )

    for index, item in enumerate(split_items(application_text)[:50], start=1):
        item_urls = extract_urls(item)
        ApplicationStepCandidate.objects.create(
            candidate=candidate,
            source_chunk=chunk_by_section["application"],
            step_number=index,
            instruction=item,
            url=item_urls[0] if item_urls else "",
            confidence=Decimal("0.70"),
        )

    return candidate


@transaction.atomic
def extract_knowledge(
    extraction: DocumentExtraction,
    *,
    force: bool = False,
) -> KnowledgeExtractionResult:
    if extraction.status != DocumentExtraction.Status.SUCCEEDED:
        raise KnowledgeExtractionError("Only successful document extractions can be processed.")

    try:
        quality = extraction.quality_assessment
    except DocumentQualityAssessment.DoesNotExist as exc:
        raise KnowledgeExtractionError("The extraction has no quality assessment.") from exc

    if not quality.usable_for_structured_extraction:
        raise KnowledgeExtractionError("The document is not approved for structured extraction.")

    version = settings.KNOWLEDGE_EXTRACTOR_VERSION
    run, created = KnowledgeExtractionRun.objects.get_or_create(
        extraction=extraction,
        extractor_version=version,
    )
    if run.status == KnowledgeExtractionRun.Status.SUCCEEDED and not force:
        return KnowledgeExtractionResult(
            run=run,
            created=False,
            unchanged=True,
            candidate_count=run.candidate_count,
        )

    run.status = KnowledgeExtractionRun.Status.RUNNING
    run.started_at = timezone.now()
    run.finished_at = None
    run.error_message = ""
    run.save(
        update_fields=[
            "status",
            "started_at",
            "finished_at",
            "error_message",
            "updated_at",
        ]
    )
    if force:
        run.candidates.all().delete()

    try:
        chunks = list(extraction.chunks.order_by("chunk_index"))
        blocks = segment_candidates(
            chunks,
            min_score=settings.KNOWLEDGE_MIN_CANDIDATE_SCORE,
            max_block_chars=settings.KNOWLEDGE_MAX_BLOCK_CHARS,
        )
        for block in blocks:
            _create_candidate(run, extraction, block)
        run.candidate_count = len(blocks)
        run.status = KnowledgeExtractionRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.metadata = {
            "quality_score": float(quality.score),
            "source_chunk_count": len(chunks),
            "candidate_pages": [
                {
                    "title": block.title,
                    "start_page": block.start_page,
                    "end_page": block.end_page,
                    "score": block.score,
                }
                for block in blocks
            ],
        }
        run.save(
            update_fields=[
                "candidate_count",
                "status",
                "finished_at",
                "metadata",
                "updated_at",
            ]
        )
    except Exception as exc:
        run.status = KnowledgeExtractionRun.Status.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "error_message",
                "updated_at",
            ]
        )
        raise

    return KnowledgeExtractionResult(
        run=run,
        created=created,
        unchanged=False,
        candidate_count=run.candidate_count,
    )
