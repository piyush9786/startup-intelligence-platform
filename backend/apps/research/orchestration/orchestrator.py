"""Framework-free workflow runner for grounded research."""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from apps.research.models import StartupResearchReport
from apps.research.services.job_state import (
    claim_research_request,
    mark_research_failed,
    persist_research_result,
)

from .dependencies import ResearchDependencies
from .state import ResearchState
from .steps import DEFAULT_RESEARCH_STEPS

logger = logging.getLogger(__name__)

ResearchStep = Callable[
    [ResearchState, ResearchDependencies],
    ResearchState,
]


class ResearchOrchestrator:
    """Run an explicit ordered list of Python workflow functions."""

    def __init__(
        self,
        *,
        steps: Sequence[ResearchStep] = DEFAULT_RESEARCH_STEPS,
        dependencies: ResearchDependencies | None = None,
    ):
        self.steps = tuple(steps)
        self.dependencies = dependencies or ResearchDependencies()

    def run(
        self,
        research_request_id: str,
        *,
        task_id: str = "",
    ) -> StartupResearchReport:
        claim = claim_research_request(
            research_request_id,
            task_id=task_id,
        )
        if claim.existing_report is not None:
            return claim.existing_report

        state = ResearchState.from_request(claim.request)

        try:
            for step in self.steps:
                state = step(state, self.dependencies)
            return persist_research_result(state)
        except Exception as exc:
            logger.exception(
                "Research orchestration failed for request %s",
                research_request_id,
            )
            mark_research_failed(
                research_request_id,
                error_code="research_failed",
                error_message=str(exc),
            )
            raise


def build_default_orchestrator(
    *,
    dependencies: ResearchDependencies | None = None,
) -> ResearchOrchestrator:
    return ResearchOrchestrator(
        dependencies=dependencies,
    )
