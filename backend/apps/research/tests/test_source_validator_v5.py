from apps.research.services.source_validator import (
    classify_source_type,
    compute_evidence_confidence,
    validate_source_url,
)


def test_official_source_remains_official():
    source_type = classify_source_type(
        "https://www.startupindia.gov.in/"
    )
    _, status = compute_evidence_confidence(
        source_type,
        0.8,
    )

    assert source_type == "official_portal"
    assert status == "official_live"


def test_reputable_news_remains_secondary():
    source_type = classify_source_type(
        "https://inc42.com/features/example"
    )
    _, status = compute_evidence_confidence(
        source_type,
        0.8,
    )

    assert source_type == "news"
    assert status == "reputable_secondary"


def test_startup_directory_low_rank_is_not_rejected():
    source_type = classify_source_type(
        "https://tracxn.com/d/explore/example"
    )
    _, status = compute_evidence_confidence(
        source_type,
        0.20,
    )

    assert source_type == "startup_directory"
    assert status == "unverified_live"


def test_unknown_but_valid_web_source_is_unverified():
    source_type = classify_source_type(
        "https://www.microsoft.com/en-us/startups"
    )
    _, status = compute_evidence_confidence(
        source_type,
        0.20,
    )

    assert source_type == "web_source"
    assert status == "unverified_live"


def test_arbitrary_valid_web_source_is_not_promoted_to_trusted():
    source_type = classify_source_type(
        "https://example.com/product"
    )
    _, status = compute_evidence_confidence(
        source_type,
        1.0,
    )

    assert source_type == "web_source"
    assert status == "unverified_live"
    assert status not in {
        "official_live",
        "reputable_secondary",
    }


def test_invalid_url_still_fails_validation():
    assert validate_source_url("not-a-url") is False
    assert validate_source_url("") is False
