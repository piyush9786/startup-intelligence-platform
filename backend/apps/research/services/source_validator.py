"""Source validation and evidence hash classification service."""
from __future__ import annotations

import hashlib
from urllib.parse import urlparse

OFFICIAL_DOMAINS = {
    "gov.in",
    "nic.in",
    "startupindia.gov.in",
    "dpiit.gov.in",
    "udyamregistration.gov.in",
    "rbi.org.in",
    "sebi.gov.in",
}

REPUTABLE_MEDIA = {
    "inc42.com",
    "yourstory.com",
    "economictimes.indiatimes.com",
    "livemint.com",
    "moneycontrol.com",
    "techcrunch.com",
    "business-standard.com",
}


def validate_source_url(url: str) -> bool:
    """Validate that a search result URL is well-formed."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _is_matching_domain(domain: str, target: str) -> bool:
    """Safe domain comparison to prevent spoofing (e.g. fakegov.in matching gov.in)."""
    return domain == target or domain.endswith(f".{target}")


def classify_source_type(url: str, publisher: str | None = None) -> str:
    """Classify the source type based on host domain and publisher."""
    domain = urlparse(url).netloc.lower()

    if any(_is_matching_domain(domain, d) for d in OFFICIAL_DOMAINS):
        return "official_portal"
    if any(_is_matching_domain(domain, d) for d in REPUTABLE_MEDIA):
        return "news"
    if "report" in url.lower() or "research" in url.lower():
        return "market_report"
    return "company_website"


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_evidence_confidence(
    source_type: str,
    retrieval_relevance: float,
) -> tuple[float, str]:
    """Calculate multi-factor confidence combining domain authority and retrieval relevance.

    Returns:
        (final_confidence_score, verification_status)
    """
    AUTHORITY_WEIGHTS = {
        "official_portal": 0.95,
        "news": 0.75,
        "market_report": 0.70,
        "company_website": 0.55,
    }

    authority_score = AUTHORITY_WEIGHTS.get(source_type, 0.5)
    # Combine 60% authority + 40% search relevance
    final_score = round(0.60 * authority_score + 0.40 * min(max(retrieval_relevance, 0.0), 1.0), 2)

    if source_type == "official_portal":
        status = "official_live"
    elif source_type in ("news", "market_report") and final_score >= 0.65:
        status = "reputable_secondary"
    elif final_score >= 0.45:
        status = "unverified_live"
    else:
        status = "rejected"

    return final_score, status


def classify_verification_status(source_type: str, confidence: float) -> str:
    _, status = compute_evidence_confidence(source_type, confidence)
    return status
