"""Tests for source validator and evidence extractor."""
from apps.research.services.evidence_extractor import extract_and_score_evidence
from apps.research.services.evidence_ranker import rank_and_deduplicate_evidence
from apps.research.services.source_validator import (
    classify_source_type,
    classify_verification_status,
    validate_source_url,
)
from apps.research.services.tavily_client import SearchResult


def test_source_validator_helpers():
    assert validate_source_url("https://startupindia.gov.in/portal") is True
    assert validate_source_url("invalid-url") is False

    assert classify_source_type("https://startupindia.gov.in") == "official_portal"
    assert classify_source_type("https://inc42.com/news") == "news"

    assert classify_verification_status("official_portal", 0.9) == "official_live"
    assert classify_verification_status("news", 0.8) == "reputable_secondary"


def test_evidence_ranking():
    results = [
        SearchResult(
            title="Official DPIIT Portal",
            url="https://dpiit.gov.in/scheme",
            content="Official scheme details",
            score=0.9,
            published_at="2026-01-01",
        ),
        SearchResult(
            title="Tech Blog Entry",
            url="https://techblog.com/post",
            content="Unverified blog post",
            score=0.5,
            published_at="2026-01-01",
        ),
    ]

    extracted = extract_and_score_evidence(results, "scheme")
    ranked = rank_and_deduplicate_evidence(extracted)

    assert len(ranked) == 2
    assert ranked[0]["title"] == "Official DPIIT Portal"
    assert ranked[0]["verification_status"] == "official_live"
