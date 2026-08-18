"""Compatibility facade for the plain-Python research orchestrator."""
from __future__ import annotations

from apps.research.orchestration.dependencies import (
    ResearchDependencies,
)
from apps.research.orchestration.orchestrator import (
    build_default_orchestrator,
)
from apps.research.services.local_retrieval import (
    retrieve_local_verified_knowledge,
)
from apps.startups.services.llm_provider import (
    get_startupintel_runtime_provider,
)

# Preserve the existing import used by current tests and callers.
_retrieve_local_verified_knowledge = (
    retrieve_local_verified_knowledge
)


def generate_research_report(
    research_request_id: str,
    *,
    task_id: str = "",
):
    """Generate one idempotent report through vanilla Python steps."""
    dependencies = ResearchDependencies(
        llm_provider_factory=(
            get_startupintel_runtime_provider
        ),
    )
    orchestrator = build_default_orchestrator(
        dependencies=dependencies,
    )
    return orchestrator.run(
        research_request_id,
        task_id=task_id,
    )
