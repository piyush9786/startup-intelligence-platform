"""Auditable hybrid search and reranking for verified startup schemes.

The service deliberately treats TF-IDF as one signal rather than the final
answer. Query intent, deterministic eligibility, structured scheme metadata,
application status, founder profile context, and evidence completeness are
combined into a transparent score. Explicit high-risk intents such as
women-focused support and loans use hard filters so unrelated schemes are not
presented as valid matches.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
from sklearn.metrics.pairwise import cosine_similarity

from apps.ml_engine.models import MLModelRegistry
from apps.recommendations.services.eligibility import evaluate_scheme_eligibility
from apps.schemes.models import Scheme, SchemeVersion

RANKING_VERSION = "hybrid-scheme-search-v1"

WEIGHTS = {
    "text": 0.30,
    "eligibility": 0.25,
    "support_type": 0.15,
    "sector": 0.10,
    "stage": 0.10,
    "location": 0.05,
    "evidence": 0.05,
}

MIN_QUERY_LENGTH = 2
MIN_TEXT_SCORE = 0.015
MIN_FINAL_SCORE = 0.24


SUPPORT_INTENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "loan": {
        "query": (
            "loan",
            "credit",
            "working capital",
            "debt",
            "guarantee",
            "collateral",
            "term finance",
            "ऋण",
            "कर्ज",
        ),
        "scheme": (
            "loan",
            "credit",
            "working capital",
            "debt",
            "guarantee",
            "collateral",
            "term finance",
            "interest rate",
        ),
    },
    "seed": {
        "query": (
            "seed funding",
            "seed fund",
            "pre seed",
            "pre-seed",
            "prototype funding",
            "early stage funding",
            "बीज निधि",
        ),
        "scheme": (
            "seed",
            "prototype",
            "proof of concept",
            "early stage",
            "incubator funding",
            "grant",
        ),
    },
    "grant": {
        "query": ("grant", "subsidy", "reimbursement", "अनुदान"),
        "scheme": ("grant", "subsidy", "reimbursement", "financial assistance"),
    },
    "tax": {
        "query": ("tax exemption", "tax benefit", "income tax", "कर छूट"),
        "scheme": ("tax exemption", "tax benefit", "80-iac", "80iac"),
    },
    "incubation": {
        "query": ("incubation", "incubator", "accelerator", "mentorship"),
        "scheme": ("incubation", "incubator", "accelerator", "mentorship", "tbi"),
    },
}

AUDIENCE_INTENTS: dict[str, tuple[str, ...]] = {
    "women": (
        "women",
        "woman",
        "female founder",
        "female entrepreneur",
        "women entrepreneur",
        "महिला",
        "महिला उद्यमी",
    ),
    "sc_st": (
        "sc st",
        "sc/st",
        "scheduled caste",
        "scheduled tribe",
        "dalit",
        "tribal entrepreneur",
    ),
    "rural": ("rural", "village", "ग्रामीण", "गांव"),
}

SECTOR_INTENTS: dict[str, tuple[str, ...]] = {
    "biotechnology": (
        "biotechnology",
        "biotech",
        "life science",
        "life sciences",
        "biopharma",
        "medtech",
    ),
    "manufacturing": (
        "manufacturing",
        "manufacturer",
        "factory",
        "production unit",
        "msme manufacturing",
        "msme",
    ),
    "agriculture": (
        "agriculture",
        "agri",
        "agritech",
        "farm",
        "food processing",
    ),
    "defence": ("defence", "defense", "military", "drdo", "idex"),
    "clean_energy": (
        "clean energy",
        "green energy",
        "solar",
        "renewable",
        "climate tech",
        "cleantech",
    ),
    "electronics": (
        "electronics",
        "semiconductor",
        "chip design",
        "hardware",
    ),
    "space": ("space tech", "spacetech", "space startup", "in-space", "inspace"),
    "software": (
        "software",
        "saas",
        "artificial intelligence",
        " ai ",
        "digital technology",
        "it startup",
    ),
}

STAGE_INTENTS: dict[str, tuple[str, ...]] = {
    "idea": ("idea stage", "idea-stage", "concept stage"),
    "validation": ("validation stage", "problem validation"),
    "prototype": ("prototype", "proof of concept", "poc"),
    "mvp": ("mvp", "minimum viable product"),
    "pilot": ("pilot stage", "pilot project"),
    "early_revenue": ("early revenue", "revenue stage"),
    "growth": ("growth stage", "scale up", "scale-up"),
    "expansion": ("expansion stage", "market expansion"),
}


@dataclass(frozen=True)
class QueryIntents:
    support_types: tuple[str, ...]
    audiences: tuple[str, ...]
    sectors: tuple[str, ...]
    stages: tuple[str, ...]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "support_types": list(self.support_types),
            "audiences": list(self.audiences),
            "sectors": list(self.sectors),
            "stages": list(self.stages),
        }


@dataclass(frozen=True)
class CandidateScore:
    scheme: Scheme
    final_score: float
    components: dict[str, float]
    matched_intents: tuple[str, ...]
    eligibility_result: str
    eligibility_reason: str
    text_score: float


class HybridSearchConfigurationError(RuntimeError):
    """Raised when the active TF-IDF artifact is missing or inconsistent."""


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(
            f"{_normalise_text(key)} {_normalise_text(item)}"
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return " ".join(_normalise_text(item) for item in value)
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    folded = text.casefold()
    return any(term.casefold() in folded for term in terms)


def detect_query_intents(query: str) -> QueryIntents:
    text = _normalise_text(query)

    support = tuple(
        name
        for name, payload in SUPPORT_INTENTS.items()
        if _contains_any(text, payload["query"])
    )
    audiences = tuple(
        name
        for name, terms in AUDIENCE_INTENTS.items()
        if _contains_any(text, terms)
    )
    sectors = tuple(
        name
        for name, terms in SECTOR_INTENTS.items()
        if _contains_any(text, terms)
    )
    stages = tuple(
        name
        for name, terms in STAGE_INTENTS.items()
        if _contains_any(text, terms)
    )

    return QueryIntents(
        support_types=support,
        audiences=audiences,
        sectors=sectors,
        stages=stages,
    )


def _scheme_text(scheme: Scheme) -> str:
    version = scheme.current_version
    if version is None:
        return ""

    rules = list(version.eligibility_rules.all())
    return _normalise_text(
        [
            scheme.canonical_name,
            scheme.short_name,
            scheme.alternative_names,
            getattr(scheme.authority, "name", ""),
            getattr(scheme.authority, "ministry", ""),
            getattr(scheme.authority, "department", ""),
            version.description,
            version.objective,
            version.support_types,
            version.categories,
            version.eligible_sectors,
            version.eligible_stages,
            version.eligible_states,
            version.founder_categories,
            version.benefits,
            version.restrictions,
            version.required_documents,
            version.application_steps,
            [
                {
                    "field": rule.field_path,
                    "expected": rule.expected_value,
                    "evidence": rule.evidence_text,
                }
                for rule in rules
            ],
        ]
    )


def _scheme_support_matches(version: SchemeVersion, text: str, intent: str) -> bool:
    if intent == "loan" and (
        version.interest_rate_min is not None or version.interest_rate_max is not None
    ):
        return True
    return _contains_any(text, SUPPORT_INTENTS[intent]["scheme"])


def _scheme_audience_matches(text: str, audience: str) -> bool:
    return _contains_any(text, AUDIENCE_INTENTS[audience])


def _scheme_sector_matches(text: str, sector: str) -> bool:
    return _contains_any(text, SECTOR_INTENTS[sector])


def _scheme_stage_matches(text: str, stage: str) -> bool:
    return _contains_any(text, STAGE_INTENTS[stage])


def _safe_ratio(matches: int, total: int, *, unknown: float = 0.5) -> float:
    if total <= 0:
        return unknown
    return max(0.0, min(1.0, matches / total))


def _profile_values(profile: Any, field_name: str) -> list[str]:
    value = getattr(profile, field_name, None)
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalise_text(item) for item in value if _normalise_text(item)]
    return [_normalise_text(value)]


def _structured_list_score(
    expected_values: Iterable[Any],
    actual_values: Iterable[Any],
    *,
    empty_expected: float = 0.60,
    empty_actual: float = 0.50,
) -> float:
    expected = {_normalise_text(value) for value in expected_values if _normalise_text(value)}
    actual = {_normalise_text(value) for value in actual_values if _normalise_text(value)}

    if not expected:
        return empty_expected
    if not actual:
        return empty_actual

    for left in expected:
        for right in actual:
            if left == right or left in right or right in left:
                return 1.0
    return 0.0


def _eligibility_component(profile: Any, version: SchemeVersion) -> tuple[float, str, str]:
    if profile is None:
        return 0.55, "not_evaluated", "No startup profile was supplied."

    evaluation = evaluate_scheme_eligibility(
        startup_profile=profile,
        scheme_version=version,
        as_of_date=date.today(),
    )
    total = (
        len(evaluation.matched_rules)
        + len(evaluation.failed_rules)
        + len(evaluation.unknown_rules)
    )
    match_ratio = _safe_ratio(len(evaluation.matched_rules), total, unknown=0.45)

    if evaluation.result == "eligible":
        return max(0.85, match_ratio), evaluation.result, evaluation.explanation
    if evaluation.result == "insufficient_information":
        return 0.55 + (0.20 * match_ratio), evaluation.result, evaluation.explanation
    if evaluation.result == "verification_required":
        return 0.48 + (0.17 * match_ratio), evaluation.result, evaluation.explanation
    if evaluation.result == "application_closed":
        return 0.0, evaluation.result, evaluation.explanation
    if evaluation.result == "ineligible":
        return 0.0, evaluation.result, evaluation.explanation
    return 0.40, evaluation.result, evaluation.explanation


def _evidence_component(version: SchemeVersion) -> float:
    document = version.source_document
    if document is None:
        return 0.0
    if document.storage_key:
        return 1.0
    if document.content_hash and document.source_url and document.final_url:
        return 0.70
    if document.source_url:
        return 0.45
    return 0.20


def _verify_checksum(entry: MLModelRegistry) -> None:
    path = Path(entry.artifact_path)
    if not path.exists():
        raise HybridSearchConfigurationError(
            f"TF-IDF artifact is missing: {entry.artifact_path!r}."
        )
    if not entry.artifact_checksum:
        return

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != entry.artifact_checksum:
        raise HybridSearchConfigurationError(
            f"TF-IDF artifact checksum mismatch for v{entry.model_version}."
        )


def _active_tfidf_bundle() -> tuple[MLModelRegistry | None, dict[str, Any] | None]:
    entry = (
        MLModelRegistry.objects.filter(
            model_type=MLModelRegistry.ModelType.TFIDF,
            status=MLModelRegistry.Status.ACTIVE,
        )
        .order_by("-model_version")
        .first()
    )
    if entry is None:
        return None, None

    _verify_checksum(entry)
    bundle = joblib.load(entry.artifact_path)
    required = {"vectorizer", "tfidf_matrix", "scheme_version_ids"}
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise HybridSearchConfigurationError(
            f"TF-IDF v{entry.model_version} has an invalid artifact shape."
        )
    return entry, bundle


def _tfidf_scores(query: str) -> tuple[dict[str, float], dict[str, Any]]:
    entry, bundle = _active_tfidf_bundle()
    if entry is None or bundle is None:
        return {}, {
            "available": False,
            "version": None,
            "stage": None,
            "production_approved": False,
        }

    query_vector = bundle["vectorizer"].transform([query])
    scores = cosine_similarity(query_vector, bundle["tfidf_matrix"]).ravel()
    ids = [str(value) for value in bundle["scheme_version_ids"]]

    return (
        {scheme_id: float(scores[index]) for index, scheme_id in enumerate(ids)},
        {
            "available": True,
            "version": entry.model_version,
            "stage": entry.deployment_stage,
            "production_approved": entry.production_approved,
            "training_sample_count": entry.training_sample_count,
        },
    )


def _profile_context_scores(profile: Any, version: SchemeVersion) -> tuple[float, float, float]:
    if profile is None:
        return 0.50, 0.50, 0.50

    sector_score = _structured_list_score(
        version.eligible_sectors or version.categories,
        _profile_values(profile, "sectors") + _profile_values(profile, "technologies"),
    )
    stage_score = _structured_list_score(
        version.eligible_stages,
        _profile_values(profile, "stage"),
    )
    location_score = _structured_list_score(
        version.eligible_states,
        _profile_values(profile, "state"),
        empty_expected=0.75,
    )
    return sector_score, stage_score, location_score


def score_scheme_candidate(
    *,
    scheme: Scheme,
    query: str,
    intents: QueryIntents,
    text_score: float,
    startup_profile: Any = None,
) -> CandidateScore | None:
    version = scheme.current_version
    if version is None or version.verification_status != SchemeVersion.VerificationStatus.VERIFIED:
        return None
    if version.application_status == SchemeVersion.ApplicationStatus.CLOSED:
        return None

    text = _scheme_text(scheme)
    matched_intents: list[str] = []

    # Hard audience constraints prevent unsupported identity-specific claims.
    for audience in intents.audiences:
        if not _scheme_audience_matches(text, audience):
            return None
        matched_intents.append(f"audience:{audience}")

    support_scores: list[float] = []
    for intent in intents.support_types:
        matched = _scheme_support_matches(version, text, intent)
        # Loan and tax are strict financial/legal intents. Seed is also strict
        # enough to prevent generic mentoring programmes from appearing.
        if intent in {"loan", "tax", "seed"} and not matched:
            return None
        support_scores.append(1.0 if matched else 0.0)
        if matched:
            matched_intents.append(f"support:{intent}")
    support_score = (
        sum(support_scores) / len(support_scores)
        if support_scores
        else 0.60
    )

    sector_scores: list[float] = []
    for sector in intents.sectors:
        matched = _scheme_sector_matches(text, sector)
        # Explicit sector queries are strict. An unrelated general scheme must
        # not outrank a sector-specific programme just because of common words.
        if not matched:
            return None
        sector_scores.append(1.0)
        matched_intents.append(f"sector:{sector}")

    profile_sector, profile_stage, location_score = _profile_context_scores(
        startup_profile,
        version,
    )
    sector_score = (
        sum(sector_scores) / len(sector_scores)
        if sector_scores
        else profile_sector
    )

    stage_scores: list[float] = []
    for stage in intents.stages:
        matched = _scheme_stage_matches(text, stage)
        if not matched:
            return None
        stage_scores.append(1.0)
        matched_intents.append(f"stage:{stage}")
    stage_score = (
        sum(stage_scores) / len(stage_scores)
        if stage_scores
        else profile_stage
    )

    eligibility_score, eligibility_result, eligibility_reason = _eligibility_component(
        startup_profile,
        version,
    )
    if eligibility_result in {"ineligible", "application_closed"}:
        return None

    evidence_score = _evidence_component(version)

    components = {
        "text": max(0.0, min(1.0, float(text_score))),
        "eligibility": eligibility_score,
        "support_type": support_score,
        "sector": sector_score,
        "stage": stage_score,
        "location": location_score,
        "evidence": evidence_score,
    }
    final_score = sum(components[key] * WEIGHTS[key] for key in WEIGHTS)

    has_explicit_intent = bool(
        intents.support_types or intents.audiences or intents.sectors or intents.stages
    )
    if text_score < MIN_TEXT_SCORE and not matched_intents and not has_explicit_intent:
        return None
    if final_score < MIN_FINAL_SCORE:
        return None

    return CandidateScore(
        scheme=scheme,
        final_score=round(final_score, 6),
        components={key: round(value, 6) for key, value in components.items()},
        matched_intents=tuple(matched_intents),
        eligibility_result=eligibility_result,
        eligibility_reason=eligibility_reason,
        text_score=round(float(text_score), 6),
    )


def _no_match_message(intents: QueryIntents) -> str:
    if "women" in intents.audiences:
        return (
            "No verified women-specific scheme was found in the current catalog. "
            "General entrepreneurship programmes were intentionally excluded."
        )
    if "loan" in intents.support_types:
        return (
            "No sufficiently relevant verified loan, credit, debt, guarantee, or "
            "working-capital scheme matched this search."
        )
    if intents.sectors:
        labels = ", ".join(intents.sectors)
        return f"No sufficiently relevant verified {labels} scheme matched this search."
    return "No sufficiently relevant verified scheme matched this search."


def hybrid_search_verified_schemes(
    *,
    query: str,
    startup_profile: Any = None,
    limit: int = 20,
) -> dict[str, Any]:
    normalized_query = re.sub(r"\s+", " ", str(query or "")).strip()
    if len(normalized_query) < MIN_QUERY_LENGTH:
        return {
            "query": normalized_query,
            "ranking_version": RANKING_VERSION,
            "detected_intents": QueryIntents((), (), (), ()).to_dict(),
            "model": {
                "available": False,
                "version": None,
                "stage": None,
                "production_approved": False,
            },
            "count": 0,
            "no_match": True,
            "message": "Enter at least two characters to search verified schemes.",
            "results": [],
        }

    limit = max(1, min(int(limit), 50))
    intents = detect_query_intents(normalized_query)
    text_scores, model_info = _tfidf_scores(normalized_query)

    schemes = list(
        Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__isnull=False,
            current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        )
        .select_related(
            "authority",
            "current_version",
            "current_version__source_document",
        )
        .prefetch_related("current_version__eligibility_rules")
        .order_by("canonical_name")
    )

    scored: list[CandidateScore] = []
    for scheme in schemes:
        candidate = score_scheme_candidate(
            scheme=scheme,
            query=normalized_query,
            intents=intents,
            text_score=text_scores.get(str(scheme.current_version_id), 0.0),
            startup_profile=startup_profile,
        )
        if candidate is not None:
            scored.append(candidate)

    scored.sort(
        key=lambda item: (
            -item.final_score,
            -item.text_score,
            item.scheme.canonical_name.casefold(),
        )
    )

    results = []
    for rank, candidate in enumerate(scored[:limit], start=1):
        version = candidate.scheme.current_version
        results.append(
            {
                "rank": rank,
                "scheme_id": str(candidate.scheme.id),
                "scheme_version_id": str(version.id),
                "scheme_name": candidate.scheme.canonical_name,
                "authority_name": candidate.scheme.authority.name,
                "final_score": candidate.final_score,
                "confidence_label": (
                    "strong"
                    if candidate.final_score >= 0.72
                    else "relevant"
                    if candidate.final_score >= 0.52
                    else "possible"
                ),
                "score_breakdown": candidate.components,
                "matched_intents": list(candidate.matched_intents),
                "eligibility_result": candidate.eligibility_result,
                "eligibility_reason": candidate.eligibility_reason,
                "application_status": version.application_status,
                "verification_status": version.verification_status,
                "evidence": {
                    "source_url": version.source_document.source_url,
                    "content_hash": version.source_document.content_hash,
                    "raw_snapshot_archived": bool(version.source_document.storage_key),
                },
            }
        )

    no_match = not results
    return {
        "query": normalized_query,
        "ranking_version": RANKING_VERSION,
        "weights": WEIGHTS,
        "detected_intents": intents.to_dict(),
        "model": model_info,
        "profile_applied": startup_profile is not None,
        "count": len(results),
        "no_match": no_match,
        "message": _no_match_message(intents) if no_match else "",
        "results": results,
    }
