"""Mutable workflow state passed through research orchestration steps."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SearchFailure:
    query: str
    error: str


@dataclass(slots=True)
class ResearchState:
    request_id: str
    request: Any
    profile: Any
    question: str

    requires_live_search: bool = False
    search_decision_reason: str = ""
    idea: dict[str, Any] = field(default_factory=dict)
    queries: list[str] = field(default_factory=list)

    raw_live_evidence: list[dict[str, Any]] = field(default_factory=list)
    live_evidence: list[dict[str, Any]] = field(default_factory=list)
    local_evidence: list[dict[str, Any]] = field(default_factory=list)
    vector_evidence: list[dict[str, Any]] = field(default_factory=list)
    prior_intelligence: list[dict[str, Any]] = field(default_factory=list)
    search_failures: list[SearchFailure] = field(default_factory=list)

    vector_retrieval_status: str = "disabled"
    vector_retrieval_error: str = ""
    context_payload: dict[str, Any] = field(default_factory=dict)
    report_data: dict[str, Any] = field(default_factory=dict)
    model_name: str = ""
    llm_status: str = "not_started"
    live_search_status: str = "not_started"

    partial_results: bool = False
    partial_messages: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, request: Any) -> ResearchState:
        return cls(
            request_id=str(request.id),
            request=request,
            profile=request.startup_profile,
            question=request.question,
        )
