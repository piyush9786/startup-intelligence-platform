"""Injectable dependencies used by research orchestration steps."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from apps.research.services.answer_context import assemble_research_context
from apps.research.services.evidence_extractor import extract_and_score_evidence
from apps.research.services.evidence_ranker import rank_and_deduplicate_evidence
from apps.research.services.local_retrieval import (
    retrieve_local_verified_knowledge,
)
from apps.research.services.search_provider import execute_web_search
from apps.research.services.vector_retrieval import (
    retrieve_startup_vector_evidence,
)
from apps.startups.services.llm_provider import (
    StartupAdvisorLLMProvider,
    get_startupintel_runtime_provider,
)


@dataclass(frozen=True, slots=True)
class ResearchDependencies:
    web_search: Callable[..., list[Any]] = execute_web_search
    extract_evidence: Callable[..., list[dict[str, Any]]] = (
        extract_and_score_evidence
    )
    rank_evidence: Callable[..., list[dict[str, Any]]] = (
        rank_and_deduplicate_evidence
    )
    retrieve_local_evidence: Callable[..., list[dict[str, Any]]] = (
        retrieve_local_verified_knowledge
    )
    retrieve_vector_evidence: Callable[..., list[dict[str, Any]]] = (
        retrieve_startup_vector_evidence
    )
    assemble_context: Callable[..., dict[str, Any]] = (
        assemble_research_context
    )
    llm_provider_factory: Callable[
        [],
        StartupAdvisorLLMProvider,
    ] = get_startupintel_runtime_provider
