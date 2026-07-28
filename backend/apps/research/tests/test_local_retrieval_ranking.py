"""Regression coverage for founder-profile catalog relevance ranking."""

from types import SimpleNamespace

from apps.research.services.local_retrieval import (
    _profile_terms,
    _rank_records,
)


def record(
    *,
    name: str,
    industry: str,
    review_status: str = "needs_review",
):
    return SimpleNamespace(
        support_name=name,
        scheme_name="",
        certificate_name="",
        industry=industry,
        review_status=review_status,
    )


def test_rank_records_excludes_zero_overlap_entries():
    relevant = record(
        name="Health Device Credit",
        industry="medical devices healthcare",
    )
    unrelated = record(
        name="Textile Export Grant",
        industry="textiles apparel",
    )

    ranked = _rank_records(
        [unrelated, relevant],
        profile_terms={"medical", "devices"},
        fields=("support_name", "industry"),
        limit=5,
    )

    assert ranked == [relevant]


def test_rank_records_processes_the_complete_iterable():
    unrelated = [
        record(
            name=f"Unrelated Support {index}",
            industry="textiles",
        )
        for index in range(300)
    ]
    relevant = record(
        name="Late Matching Support",
        industry="agritech irrigation",
    )

    ranked = _rank_records(
        iter([*unrelated, relevant]),
        profile_terms={"agritech", "irrigation"},
        fields=("support_name", "industry"),
        limit=5,
    )

    assert ranked == [relevant]


def test_verified_record_wins_an_equal_relevance_tie():
    unverified = record(
        name="A Health Support",
        industry="healthcare",
    )
    verified = record(
        name="Z Health Support",
        industry="healthcare",
        review_status="verified",
    )

    ranked = _rank_records(
        [unverified, verified],
        profile_terms={"healthcare"},
        fields=("support_name", "industry"),
        limit=2,
    )

    assert ranked == [verified, unverified]


def test_profile_terms_remove_generic_catalog_words():
    profile = SimpleNamespace(
        startup_name="Startup India Funding Company",
        description="Healthcare diagnostics platform",
        stage="Idea",
        state="Karnataka",
        district="Bengaluru Urban",
        sectors=["Healthcare"],
        technologies=["Diagnostics"],
        resource_needs=["Funding"],
        funding_purpose="Growth capital",
        revenue_stage="Early",
        profile_data={},
    )

    terms = _profile_terms(profile)

    assert "startup" not in terms
    assert "funding" not in terms
    assert "idea" not in terms
    assert {"healthcare", "diagnostics", "karnataka", "bengaluru"} <= terms
