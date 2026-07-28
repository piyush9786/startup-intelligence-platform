"""Regression tests for the plain-Python research orchestrator."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.research.models import (
    ResearchRequest,
    StartupResearchReport,
)
from apps.research.orchestration.dependencies import (
    ResearchDependencies,
)
from apps.research.orchestration.orchestrator import (
    ResearchOrchestrator,
)
from apps.research.services.job_state import (
    recover_stale_research_requests,
)
from apps.startups.models import StartupProfile

User = get_user_model()


def _completed_state_step(order):
    def step(state, dependencies):
        del dependencies
        order.append("complete")
        state.local_evidence = [
            {
                "title": "Verified Profile",
                "url": (
                    f"internal://startups/{state.profile.id}"
                ),
            }
        ]
        state.context_payload = {"evidence": "verified"}
        state.report_data = {
            "startup_summary": "Grounded summary",
            "historical_peers": [],
            "current_competitors": [],
            "recent_market_developments": [],
            "government_schemes": [],
            "compliance_requirements": [],
            "funding_opportunities": [],
            "loan_options": [],
            "risks": [],
            "market_gaps": [],
            "capital_scenarios": "Validate costs.",
            "recommended_next_actions": [],
            "sources": [
                f"internal://startups/{state.profile.id}",
            ],
            "confidence_score": 0.8,
            "research_metadata": {
                "live_search_status": "not_required",
                "llm_status": "generated",
            },
        }
        state.model_name = "test-model"
        return state

    return step


@pytest.mark.django_db
def test_orchestrator_runs_steps_in_order_and_persists_once():
    user = User.objects.create_user(
        username="orchestrator-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Orchestrated Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="Explain our verified position.",
    )
    order = []

    def first(state, dependencies):
        del dependencies
        order.append("first")
        return state

    orchestrator = ResearchOrchestrator(
        steps=[
            first,
            _completed_state_step(order),
        ],
        dependencies=ResearchDependencies(),
    )

    report = orchestrator.run(str(request.id))
    second_report = orchestrator.run(str(request.id))

    assert order == ["first", "complete"]
    assert report.id == second_report.id
    assert StartupResearchReport.objects.filter(
        research_request=request,
    ).count() == 1

    request.refresh_from_db()
    assert request.status == ResearchRequest.Status.SUCCEEDED


@pytest.mark.django_db
def test_unexpected_step_failure_marks_request_failed():
    user = User.objects.create_user(
        username="failed-orchestrator-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Failure Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="Trigger a controlled failure.",
    )

    def explode(state, dependencies):
        del state, dependencies
        raise RuntimeError("controlled orchestration failure")

    orchestrator = ResearchOrchestrator(
        steps=[explode],
        dependencies=ResearchDependencies(),
    )

    with pytest.raises(
        RuntimeError,
        match="controlled orchestration failure",
    ):
        orchestrator.run(str(request.id))

    request.refresh_from_db()
    assert request.status == ResearchRequest.Status.FAILED
    assert request.error_code == "research_failed"


@pytest.mark.django_db
def test_recovery_releases_stale_running_job(settings):
    settings.RESEARCH_JOB_QUEUE_TIMEOUT_SECONDS = 900
    settings.RESEARCH_JOB_RUNNING_TIMEOUT_SECONDS = 60
    settings.RESEARCH_STALE_RECOVERY_BATCH_SIZE = 100

    user = User.objects.create_user(
        username="stale-research-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Stale Research Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="A stale running request.",
        status=ResearchRequest.Status.RUNNING,
    )

    request.started_at = timezone.now() - timedelta(
        minutes=5,
    )
    request.save(update_fields=["started_at", "updated_at"])

    recovered = recover_stale_research_requests()

    assert recovered == 1
    request.refresh_from_db()
    assert request.status == ResearchRequest.Status.FAILED
    assert request.error_code == "worker_interrupted"

    replacement = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="A replacement request.",
    )
    assert replacement.status == ResearchRequest.Status.QUEUED
