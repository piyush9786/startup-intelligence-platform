from types import SimpleNamespace

from apps.research.orchestration.steps import (
    _research_field_for_finding,
    _startupintel_compact_research_to_legacy_report,
)


def _state():
    return SimpleNamespace(
        context_payload={
            "pre_computed_analytics": {
                "estimated_capital_scenarios": {
                    "lean_prototype": (
                        "₹2,00,000 - ₹4,00,000"
                    ),
                },
            },
        },
        profile=SimpleNamespace(
            startup_name="Grounded Startup",
        ),
        idea={
            "product": "observability platform",
        },
        live_evidence=[
            {
                "url": (
                    "https://example.gov/"
                    "startup-support"
                ),
                "content_excerpt": (
                    "Generic official portal text."
                ),
            },
        ],
        vector_evidence=[],
        local_evidence=[
            {
                "title": (
                    "Official Scheme: "
                    "Example Programme"
                ),
                "url": (
                    "https://example.gov/"
                    "scheme"
                ),
            },
        ],
        requires_live_search=True,
    )


def test_unknown_finding_is_not_market_development():
    assert (
        _research_field_for_finding(
            "Official portal",
            "General information for founders.",
        )
        is None
    )


def test_real_market_finding_is_classified():
    assert (
        _research_field_for_finding(
            "DeepTech market trend",
            (
                "Enterprise adoption is "
                "increasing."
            ),
        )
        == "recent_market_developments"
    )


def test_generated_report_does_not_inherit_fallback_sections():
    result = (
        _startupintel_compact_research_to_legacy_report(
            state=_state(),
            compact_payload={
                "executive_summary": (
                    "Grounded synthesis."
                ),
                "findings": [],
                "risks_or_unknowns": [],
                "source_quality_note": (
                    "Official evidence supplied."
                ),
            },
            evidence_map={},
            used_aliases=[],
        )
    )

    assert result[
        "startup_summary"
    ] == "Grounded synthesis."

    for field in (
        "historical_peers",
        "current_competitors",
        "recent_market_developments",
        "government_schemes",
        "compliance_requirements",
        "funding_opportunities",
        "loan_options",
        "risks",
        "market_gaps",
    ):
        assert result[field] == []

    assert result[
        "recommended_next_actions"
    ] == [
        (
            "Run the Requirements workspace and verify "
            "sector-specific compliance and certification "
            "obligations against official sources."
        ),
        (
            "Run a dedicated competitor-validation search using "
            "primary company sources before treating any startup "
            "as a direct competitor."
        ),
    ]

    assert (
        result["capital_scenarios"]
        == (
            "Lean prototype scenario: "
            "₹2,00,000 - ₹4,00,000"
        )
    )


def test_unverified_generated_finding_becomes_market_signal():
    finding = (
        "Deep tech investment activity is increasing "
        "across the market."
    )

    result = (
        _startupintel_compact_research_to_legacy_report(
            state=_state(),
            compact_payload={
                "executive_summary": (
                    "Grounded synthesis."
                ),
                "findings": [
                    {
                        "title": (
                            "Deep Tech Market Trend"
                        ),
                        "finding": finding,
                        "confidence": "medium",
                        "evidence_ids": [
                            "EVIDENCE_001",
                        ],
                    },
                ],
                "risks_or_unknowns": [],
                "source_quality_note": (
                    "Unverified market evidence."
                ),
            },
            evidence_map={
                "EVIDENCE_001": {
                    "verification_status": (
                        "unverified_live"
                    ),
                    "confidence_score": 0.5,
                    "url": (
                        "https://example.com/"
                        "market"
                    ),
                },
            },
            used_aliases=[
                "EVIDENCE_001",
            ],
        )
    )

    assert result[
        "recent_market_developments"
    ] == [
        (
            "Unverified market signal: "
            f"{finding}"
        ),
    ]

    assert result[
        "funding_opportunities"
    ] == []


def test_mixed_trust_generated_finding_is_withheld():
    finding = (
        "The startup operates in a priority "
        "deep-tech market."
    )

    result = (
        _startupintel_compact_research_to_legacy_report(
            state=_state(),
            compact_payload={
                "executive_summary": (
                    "Grounded synthesis."
                ),
                "findings": [
                    {
                        "title": (
                            "Mixed Evidence Finding"
                        ),
                        "finding": finding,
                        "confidence": "medium",
                        "evidence_ids": [
                            "EVIDENCE_001",
                            "EVIDENCE_002",
                        ],
                    },
                ],
                "risks_or_unknowns": [],
                "source_quality_note": (
                    "Mixed source quality."
                ),
            },
            evidence_map={
                "EVIDENCE_001": {
                    "verification_status": (
                        "verified_internal"
                    ),
                    "confidence_score": 0.9,
                    "url": (
                        "internal://startup/test"
                    ),
                },
                "EVIDENCE_002": {
                    "verification_status": (
                        "unverified_live"
                    ),
                    "confidence_score": 0.5,
                    "url": (
                        "https://example.com/"
                        "market"
                    ),
                },
            },
            used_aliases=[
                "EVIDENCE_001",
                "EVIDENCE_002",
            ],
        )
    )

    assert result[
        "recent_market_developments"
    ] == []

    assert result[
        "funding_opportunities"
    ] == []

    assert any(
        "mixed-confidence finding was withheld"
        in risk.lower()
        for risk in result["risks"]
    )
