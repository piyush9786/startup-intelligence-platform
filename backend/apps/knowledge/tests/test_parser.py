from dataclasses import dataclass

from apps.knowledge.services.parser import (
    CandidateBlock,
    classify_section,
    detect_kind,
    parse_amounts,
    parse_rules,
    segment_candidates,
    title_from_chunk,
)


@dataclass
class Chunk:
    id: int
    chunk_index: int
    heading: str
    page_number: int | None
    text: str


def test_segments_two_scheme_candidates():
    chunks = [
        Chunk(
            1,
            0,
            "Page 1",
            1,
            (
                "Startup Seed Fund Scheme\nEligibility\n"
                "DPIIT recognised startups incorporated in India may apply."
            ),
        ),
        Chunk(
            2,
            1,
            "Benefits",
            2,
            "Benefits include grant support of INR 20 lakh.",
        ),
        Chunk(
            3,
            2,
            "Page 3",
            3,
            (
                "Credit Guarantee Scheme for Startups\nEligibility\n"
                "DPIIT recognised startups can apply."
            ),
        ),
        Chunk(
            4,
            3,
            "How to apply",
            4,
            "How to apply through the official application portal.",
        ),
    ]

    blocks = segment_candidates(chunks, min_score=3)

    assert [block.title for block in blocks] == [
        "Startup Seed Fund Scheme",
        "Credit Guarantee Scheme for Startups",
    ]
    assert blocks[0].start_page == 1
    assert blocks[1].end_page == 4


def test_parses_amount_and_kind():
    amounts = parse_amounts("Grant support up to INR 20 lakh is available.")

    assert amounts[0].value == 2_000_000
    assert detect_kind("Startup Seed Fund Scheme") == "fund"


def test_classifies_sections():
    assert classify_section("Eligibility Criteria", "") == "eligibility"
    assert classify_section("How to Apply", "") == "application"
    assert classify_section("Documents Required", "") == "document"


def test_parses_atomic_rules():
    rules = parse_rules(
        "DPIIT recognised startups incorporated in India and not more "
        "than 10 years old are eligible. Annual turnover must not exceed "
        "INR 100 crore."
    )
    values = {(rule.field_name, rule.operator) for rule in rules}

    assert ("dpiit_recognized", "eq") in values
    assert ("country_of_incorporation", "eq") in values
    assert ("startup_age_months", "lte") in values
    assert ("annual_turnover_inr", "lte") in values


def test_ignores_repeated_publication_header():
    chunks = [
        Chunk(
            1,
            0,
            "Page 1",
            1,
            (
                "PLAYBOOK OF GOVERNMENT SCHEMES AND "
                "INITIATIVES FOR STARTUPS\n"
                "Startup Seed Fund Scheme\n"
                "Eligibility\n"
                "DPIIT recognised startups may apply."
            ),
        ),
        Chunk(
            2,
            1,
            "Page 2",
            2,
            (
                "PLAYBOOK OF GOVERNMENT SCHEMES AND "
                "INITIATIVES FOR STARTUPS\n"
                "Benefits include grant support of INR 20 lakh."
            ),
        ),
        Chunk(
            3,
            2,
            "Page 3",
            3,
            (
                "Credit Guarantee Scheme for Startups\n"
                "Eligibility\n"
                "DPIIT recognised startups may apply."
            ),
        ),
        Chunk(
            4,
            3,
            "Page 4",
            4,
            "How to apply through the official portal.",
        ),
    ]

    blocks = segment_candidates(
        chunks,
        min_score=3,
    )

    titles = [block.title for block in blocks]

    assert "PLAYBOOK OF GOVERNMENT SCHEMES AND INITIATIVES FOR STARTUPS" not in titles
    assert "Startup Seed Fund Scheme" in titles
    assert "Credit Guarantee Scheme for Startups" in titles


def test_removes_scheme_list_number_from_title():
    chunk = Chunk(
        1,
        0,
        "Page 14",
        14,
        (
            "4 Biotechnology Ignition Grant\n"
            "Eligibility\n"
            "Eligible biotechnology startups may apply.\n"
            "Benefits include grant funding."
        ),
    )

    assert title_from_chunk(chunk) == "Biotechnology Ignition Grant"


def test_joins_wrapped_title_ending_with_ampersand():
    chunk = Chunk(
        1,
        0,
        "Page 23",
        23,
        (
            "12 Support for International Patent "
            "Protection in Electronics &\n"
            "Information Technology\n"
            "Eligibility\n"
            "Eligible startups may apply for financial support."
        ),
    )

    blocks = segment_candidates(
        [chunk],
        min_score=3,
    )

    assert blocks[0].title == (
        "Support for International Patent Protection in Electronics & Information Technology"
    )


def test_rejects_sentence_fragment_as_candidate_title():
    chunk = Chunk(
        1,
        0,
        "Page 1",
        1,
        (
            "Digital Communication Innovation Square (DCIS) "
            "supports startups and innovators in developing new "
            "digital communication technologies so India can grow.\n"
            "Benefits include grant funding."
        ),
    )

    assert (
        segment_candidates(
            [chunk],
            min_score=3,
        )
        == []
    )


def test_rejects_generic_scheme_heading():
    chunk = Chunk(
        1,
        0,
        "Page 1",
        1,
        ("Scheme\nEligibility\nEligible startups can apply.\nBenefits include grant assistance."),
    )

    assert (
        segment_candidates(
            [chunk],
            min_score=3,
        )
        == []
    )


def test_only_first_chunk_on_page_can_start_boundary():
    chunks = [
        Chunk(
            1,
            0,
            "Page 1",
            1,
            (
                "Startup Seed Fund Scheme\n"
                "Eligibility\n"
                "DPIIT recognised startups may apply.\n"
                "Benefits include INR 20 lakh."
            ),
        ),
        Chunk(
            2,
            1,
            "Page 1",
            1,
            ("The scheme supports proof of concept development.\nApplication process is online."),
        ),
    ]

    blocks = segment_candidates(
        chunks,
        min_score=3,
    )

    assert len(blocks) == 1
    assert blocks[0].title == "Startup Seed Fund Scheme"
    assert len(blocks[0].chunks) == 2


def test_splits_inline_sections_inside_chunk():
    from apps.knowledge.services.parser import (
        split_block_sections,
    )

    chunk = Chunk(
        1,
        0,
        "Page 1",
        1,
        (
            "Startup Seed Fund Scheme\n"
            "Objective: Support proof of concept and prototype work.\n"
            "Eligibility: DPIIT recognised startups may apply.\n"
            "Benefits: Grant support up to INR 20 lakh.\n"
            "Documents Required: DPIIT recognition certificate.\n"
            "How to Apply: Submit an application on the official portal."
        ),
    )

    block = segment_candidates(
        [chunk],
        min_score=3,
    )[0]
    values, evidence = split_block_sections(block)

    assert "DPIIT recognised" in values["eligibility"][0]
    assert "INR 20 lakh" in values["benefit"][0]
    assert "recognition certificate" in values["document"][0]
    assert "official portal" in values["application"][0]
    assert evidence["eligibility"] == [chunk]


def test_strips_unpunctuated_numeric_title_prefix():
    chunk = Chunk(
        1,
        0,
        "Page 14",
        14,
        (
            "36 Equity Fund Scheme (NEDFi)\n"
            "Eligibility\n"
            "Eligible enterprises may apply.\n"
            "Benefits include equity funding assistance."
        ),
    )

    blocks = segment_candidates(
        [chunk],
        min_score=3,
    )

    assert blocks[0].title == "Equity Fund Scheme (NEDFi)"


def test_strips_page_prefix_and_joins_wrapped_title():
    chunk = Chunk(
        1,
        0,
        "Page 44",
        44,
        (
            "PLAYBOOK OF GOVERNMENT SCHEMES AND INITIATIVES FOR STARTUPS\n"
            "Page 44 of 107\n"
            "Biotechnology Innovation Fund – Accelerating\n"
            "Entrepreneurs (AcE)\n"
            "Department of Biotechnology\n"
            "WHO CAN APPLY?\n"
            "Biotech startups may apply.\n"
            "WHAT DO YOU GET?\n"
            "Funding assistance is available."
        ),
    )

    blocks = segment_candidates([chunk], min_score=3)

    assert blocks[0].title == ("Biotechnology Innovation Fund – Accelerating Entrepreneurs (AcE)")


def test_rejects_master_summary_table_page():
    chunk = Chunk(
        1,
        0,
        "Page 13",
        13,
        (
            "Page 13 of 107\n"
            "Master Summary Table\n"
            "Structured reference for all 65+ Central Government schemes\n"
            "Startup India Seed Fund Scheme\n"
            "DPIIT recognised startups may apply."
        ),
    )

    assert segment_candidates([chunk], min_score=3) == []


def test_parses_split_visual_section_headings():
    from apps.knowledge.services.parser import split_block_sections

    chunk = Chunk(
        1,
        0,
        "Page 33",
        33,
        (
            "Fund of Funds for Startups (FFS)\n"
            "🎯\n"
            "OBJECTIVES\n"
            "Catalyse venture investment.\n"
            "✅ WHO\n"
            "CAN APPLY?\n"
            "SEBI-registered AIFs can apply.\n"
            "💰 WHAT DO\n"
            "YOU GET?\n"
            "The corpus is INR 10,000 crore.\n"
            "🚀 HOW TO\n"
            "APPLY\n"
            "Apply through the SIDBI portal."
        ),
    )

    block = CandidateBlock(
        title="Fund of Funds for Startups (FFS)",
        chunks=[chunk],
        start_page=33,
        end_page=33,
    )
    values, _evidence = split_block_sections(block)

    assert "SEBI-registered AIFs" in values["eligibility"][0]
    assert "INR 10,000 crore" in values["benefit"][0]
    assert "SIDBI portal" in values["application"][0]


def test_truncates_prose_after_scheme_title():
    chunk = Chunk(
        1,
        0,
        "Page 42",
        42,
        (
            "PRISM (Promoting Innovations in Individuals, Start-ups and MSMEs) "
            "Scheme supports individual innovators with financial assistance.\n"
            "WHO CAN APPLY?\n"
            "Individual innovators may apply.\n"
            "WHAT DO YOU GET?\n"
            "Grant support is available."
        ),
    )

    blocks = segment_candidates([chunk], min_score=3)

    assert blocks[0].title == (
        "PRISM (Promoting Innovations in Individuals, Start-ups and MSMEs) Scheme"
    )


def test_parse_rules_emits_reviewable_entity_rules():
    rules = parse_rules("DPIIT-recognised Indian startups and SEBI-registered AIFs can apply.")
    signatures = {(rule.field_name, rule.operator, str(rule.value)) for rule in rules}

    assert ("dpiit_recognized", "eq", "True") in signatures
    assert (
        "country_of_incorporation",
        "eq",
        "India",
    ) in signatures
    assert (
        "eligible_entity_type",
        "contains",
        "startup",
    ) in signatures
    assert (
        "eligible_entity_type",
        "contains",
        "alternative_investment_fund",
    ) in signatures
