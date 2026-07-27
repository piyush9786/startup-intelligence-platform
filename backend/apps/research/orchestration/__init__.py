"""Plain-Python orchestration for grounded startup research."""

from .orchestrator import ResearchOrchestrator, build_default_orchestrator

__all__ = [
    "ResearchOrchestrator",
    "build_default_orchestrator",
]
