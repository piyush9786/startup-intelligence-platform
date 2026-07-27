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


def classify_source_type(url: str, publisher: str | None = None) -> str:
    """Classify the source type based on host domain and publisher."""
    domain = urlparse(url).netloc.lower()

    if any(domain.endswith(d) for d in OFFICIAL_DOMAINS):
        return "official_portal"
    if any(domain.endswith(d) for d in REPUTABLE_MEDIA):
        return "news"
    if "report" in url.lower() or "research" in url.lower():
        return "market_report"
    return "company_website"


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_verification_status(source_type: str, confidence: float) -> str:
    """Assign a verification status label based on source authority."""
    if source_type == "official_portal":
        return "official_live"
    if source_type == "news" and confidence >= 0.7:
        return "reputable_secondary"
    if confidence >= 0.5:
        return "unverified_live"
    return "rejected"
