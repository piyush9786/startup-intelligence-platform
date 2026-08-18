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

STARTUP_DIRECTORIES = {
    "tracxn.com",
    "f6s.com",
    "growthlist.co",
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
    if any(
        _is_matching_domain(domain, d)
        for d in REPUTABLE_MEDIA
    ):
        return "news"

    if any(
        _is_matching_domain(domain, d)
        for d in STARTUP_DIRECTORIES
    ):
        return "startup_directory"

    if (
        "report" in url.lower()
        or "research" in url.lower()
    ):
        return "market_report"

    # An arbitrary web domain is NOT automatically
    # the official website of a company. Treat it as
    # an unknown web source until explicitly trusted.
    return "web_source"


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_evidence_confidence(
    source_type: str,
    retrieval_relevance: float,
) -> tuple[float, str]:
    """Score evidence authority without confusing low trust with invalidity.

    Search-provider relevance affects ranking, while source type determines
    the verification tier. A valid but unknown web result remains usable as
    unverified evidence rather than being silently discarded.
    """
    AUTHORITY_WEIGHTS = {
        "official_portal": 0.95,
        "news": 0.75,
        "market_report": 0.70,
        "startup_directory": 0.50,
        "web_source": 0.15,
    }

    authority_score = AUTHORITY_WEIGHTS.get(
        source_type,
        0.15,
    )

    relevance = min(
        max(float(retrieval_relevance), 0.0),
        1.0,
    )

    final_score = round(
        0.60 * authority_score
        + 0.40 * relevance,
        2,
    )

    if source_type == "official_portal":
        status = "official_live"

    elif source_type in {
        "news",
        "market_report",
    }:
        # Recognised secondary sources remain stronger than generic
        # web results. Very weak matches are retained but downgraded.
        if final_score >= 0.55:
            status = "reputable_secondary"
        else:
            status = "unverified_live"

    elif source_type in {
        "startup_directory",
        "web_source",
    }:
        # Low authority means unverified, not invalid.
        # Confidence still controls ranking.
        status = "unverified_live"

    else:
        status = "unverified_live"

    return final_score, status

def classify_verification_status(source_type: str, confidence: float) -> str:
    _, status = compute_evidence_confidence(source_type, confidence)
    return status
