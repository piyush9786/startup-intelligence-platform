from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.schemes.models import SchemeVersion
from apps.schemes.services.hybrid_search import (
    detect_query_intents,
    hybrid_search_verified_schemes,
    score_scheme_candidate,
)


class _RuleManager:
    def all(self):
        return []


def _scheme(
    *,
    name="General programme",
    description="General startup support and mentoring.",
    support_types=None,
    sectors=None,
    founder_categories=None,
    storage_key="sources/evidence.html",
    interest_rate=None,
):
    document = SimpleNamespace(
        storage_key=storage_key,
        content_hash="abc123",
        source_url="https://example.gov/scheme",
        final_url="https://example.gov/scheme",
    )
    version = SimpleNamespace(
        id="version-1",
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        application_status=SchemeVersion.ApplicationStatus.OPEN,
        interest_rate_min=interest_rate,
        interest_rate_max=None,
        description=description,
        objective="",
        support_types=support_types or [],
        categories=sectors or [],
        eligible_sectors=sectors or [],
        eligible_stages=[],
        eligible_states=[],
        founder_categories=founder_categories or [],
        benefits=[],
        restrictions=[],
        required_documents=[],
        application_steps=[],
        eligibility_rules=_RuleManager(),
        source_document=document,
    )
    authority = SimpleNamespace(name="Official authority", ministry="", department="")
    scheme = SimpleNamespace(
        id="scheme-1",
        canonical_name=name,
        short_name="",
        alternative_names=[],
        authority=authority,
        current_version=version,
    )
    return scheme


class HybridSchemeSearchTests(SimpleTestCase):
    def test_detects_high_value_query_intents(self):
        intents = detect_query_intents(
            "seed funding and loan support for a biotechnology startup"
        )

        self.assertIn("seed", intents.support_types)
        self.assertIn("loan", intents.support_types)
        self.assertIn("biotechnology", intents.sectors)

    def test_women_query_rejects_general_programmes(self):
        scheme = _scheme()
        intents = detect_query_intents("women entrepreneur government scheme")

        candidate = score_scheme_candidate(
            scheme=scheme,
            query="women entrepreneur government scheme",
            intents=intents,
            text_score=0.30,
        )

        self.assertIsNone(candidate)

    def test_women_query_accepts_explicit_women_programme(self):
        scheme = _scheme(
            name="Women Entrepreneurship Grant",
            description="Grant support for women entrepreneurs and female founders.",
            support_types=["grant"],
            founder_categories=["women entrepreneurs"],
        )
        intents = detect_query_intents("women entrepreneur government grant")

        candidate = score_scheme_candidate(
            scheme=scheme,
            query="women entrepreneur government grant",
            intents=intents,
            text_score=0.35,
        )

        self.assertIsNotNone(candidate)
        self.assertIn("audience:women", candidate.matched_intents)

    def test_loan_query_rejects_certification_programme(self):
        scheme = _scheme(
            name="Sustainable Certification",
            description="Quality certification and assessment support.",
            support_types=["certification"],
        )
        intents = detect_query_intents("loan support for manufacturing MSME")

        candidate = score_scheme_candidate(
            scheme=scheme,
            query="loan support for manufacturing MSME",
            intents=intents,
            text_score=0.40,
        )

        self.assertIsNone(candidate)

    def test_biotechnology_grant_receives_structured_matches(self):
        scheme = _scheme(
            name="Biotechnology Innovation Grant",
            description="Biotechnology innovation grant for life-science startups.",
            support_types=["grant"],
            sectors=["biotechnology", "life sciences"],
        )
        intents = detect_query_intents("biotechnology innovation grant")

        candidate = score_scheme_candidate(
            scheme=scheme,
            query="biotechnology innovation grant",
            intents=intents,
            text_score=0.40,
        )

        self.assertIsNotNone(candidate)
        self.assertGreater(candidate.final_score, 0.50)
        self.assertEqual(candidate.components["support_type"], 1.0)
        self.assertEqual(candidate.components["sector"], 1.0)

    def test_short_query_returns_no_match_without_loading_models(self):
        payload = hybrid_search_verified_schemes(query="a")

        self.assertTrue(payload["no_match"])
        self.assertEqual(payload["results"], [])
