from __future__ import annotations

import re
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from apps.discovery.models import DocumentQualityAssessment
from apps.documents.models import DocumentExtraction
from apps.sources.services.storage import download_bytes

from .classifier import classify_page

POSITIVE_SIGNALS = {
    "eligibility": 15,
    "benefits": 12,
    "how to apply": 12,
    "application process": 12,
    "documents required": 12,
    "required documents": 12,
    "funding amount": 10,
    "loan amount": 10,
    "maximum amount": 8,
    "interest rate": 8,
    "implementing agency": 8,
    "objective": 6,
    "deadline": 6,
    "selection process": 6,
    "official website": 4,
}
NEGATIVE_SIGNALS = {
    "forgot your password": 15,
    "change password": 15,
    "otp not received": 15,
    "please login": 15,
    "select language": 8,
    "privacy policy": 4,
    "terms of use": 4,
    "cookie policy": 4,
    "users have visited": 5,
}


@dataclass(frozen=True)
class QualityResult:
    assessment: DocumentQualityAssessment
    score: float


def _repeated_line_ratio(text: str) -> float:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if not lines:
        return 1.0
    return 1 - (len(set(lines)) / len(lines))


def assess_extraction(extraction: DocumentExtraction) -> QualityResult:
    text = download_bytes(
        extraction.text_storage_key,
        bucket_name=settings.MINIO_BUCKET_PROCESSED,
    ).decode("utf-8", errors="replace")
    lower = text.lower()
    title = extraction.detected_title or extraction.source_document.title
    url = extraction.source_document.final_url or extraction.source_document.source_url
    page_type = classify_page(url=url, title=title, text=text)

    score = 0.0
    positives: list[dict[str, object]] = []
    negatives: list[dict[str, object]] = []

    words = len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))
    if words >= 1500:
        score += 12
        positives.append({"signal": "substantial_content", "points": 12})
    elif words >= 500:
        score += 8
        positives.append({"signal": "adequate_content", "points": 8})
    elif words >= 200:
        score += 3
        positives.append({"signal": "minimum_content", "points": 3})
    else:
        score -= 20
        negatives.append({"signal": "too_few_words", "points": -20})

    for signal, points in POSITIVE_SIGNALS.items():
        if signal in lower:
            score += points
            positives.append({"signal": signal, "points": points})

    for signal, points in NEGATIVE_SIGNALS.items():
        if signal in lower:
            score -= points
            negatives.append({"signal": signal, "points": -points})

    repeated_ratio = _repeated_line_ratio(text)
    if repeated_ratio > 0.45:
        score -= 18
        negatives.append(
            {
                "signal": "high_repeated_line_ratio",
                "value": round(repeated_ratio, 3),
                "points": -18,
            }
        )

    detail_types = {
        "scheme_detail",
        "loan_detail",
        "registration_detail",
        "certificate_detail",
        "benefit_detail",
        "incubator_detail",
        "guideline_pdf",
        "policy_pdf",
    }
    if page_type in detail_types:
        score += 12
        positives.append({"signal": "detail_page_type", "points": 12})
    elif page_type in {"login", "error", "asset"}:
        score -= 35
        negatives.append({"signal": f"page_type_{page_type}", "points": -35})

    if page_type in {"landing", "listing", "category"}:
        score = min(score, 40.0)
        negatives.append(
            {
                "signal": "discovery_only_page_type",
                "points": 0,
            }
        )

    score = max(0.0, min(100.0, score))
    positive_names = {str(item["signal"]) for item in positives}
    strong_sections = len(
        positive_names
        & {
            "eligibility",
            "benefits",
            "how to apply",
            "application process",
            "documents required",
            "required documents",
            "funding amount",
            "loan amount",
        }
    )

    usable_for_discovery = page_type not in {"login", "error", "asset"} and words >= 100
    usable_for_rag = score >= settings.DISCOVERY_MIN_RAG_SCORE
    usable_for_structured = (
        score >= settings.DISCOVERY_MIN_STRUCTURED_SCORE
        and page_type in detail_types
        and strong_sections >= 2
    )
    rejection_reason = ""
    if not usable_for_rag:
        rejection_reason = "Content quality score is below the RAG threshold."
    if page_type in {"login", "error", "asset"}:
        rejection_reason = f"Page classified as {page_type}."

    assessment, _ = DocumentQualityAssessment.objects.update_or_create(
        extraction=extraction,
        defaults={
            "page_type": page_type,
            "score": score,
            "positive_signals": positives,
            "negative_signals": negatives,
            "usable_for_discovery": usable_for_discovery,
            "usable_for_rag": usable_for_rag,
            "usable_for_structured_extraction": usable_for_structured,
            "rejection_reason": rejection_reason,
            "assessor_version": settings.DISCOVERY_ASSESSOR_VERSION,
            "assessed_at": timezone.now(),
        },
    )
    return QualityResult(assessment=assessment, score=score)
