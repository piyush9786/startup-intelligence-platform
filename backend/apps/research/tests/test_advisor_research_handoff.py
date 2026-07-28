"""Tests for durable advisor-to-research handoff repair."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.research.models import ResearchRequest
from apps.research.services.advisor_trigger import (
    queue_research_after_advisor,
)
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupProfile,
)

User = get_user_model()


@pytest.fixture
def advisor_briefing():
    user = User.objects.create_user(
        username="advisor-handoff-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Handoff Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    snapshot = StartupAdvisorSnapshot.objects.create(
        requested_by=user,
        startup_profile=profile,
        has_readiness_assessment=False,
        has_action_plan=False,
        has_recommendation_generation=False,
        profile_snapshot={},
        readiness_snapshot={},
        action_plan_snapshot={},
        recommendation_generation_snapshot={},
        recommendations_snapshot=[],
        recommendation_count=0,
    )
    briefing = StartupAdvisorBriefing.objects.create(
        requested_by=user,
        startup_profile=profile,
        source_snapshot=snapshot,
        provider="ollama",
        model_name="qwen3:4b",
        prompt_version="test-prompt",
        schema_version="test-schema",
        generation_parameters={},
        prompt_snapshot={},
        briefing={},
        response_metadata={},
        completed_at=timezone.now(),
    )
    StartupAdvisorBriefingJob.objects.create(
        requested_by=user,
        startup_profile=profile,
        source_snapshot=snapshot,
        status=StartupAdvisorBriefingJob.Status.SUCCEEDED,
        briefing=briefing,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )
    return user, profile, briefing


@pytest.mark.django_db
def test_handoff_is_idempotent(
    advisor_briefing,
    monkeypatch,
    settings,
):
    settings.AUTO_RESEARCH_AFTER_ADVISOR_ENABLED = True
    user, _, briefing = advisor_briefing
    monkeypatch.setattr(
        "apps.research.tasks.generate_research_report_task.delay",
        lambda *args, **kwargs: SimpleNamespace(id="task-one"),
    )

    first, first_dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )
    second, second_dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )

    assert first_dispatched is True
    assert second_dispatched is False
    assert first.id == second.id
    assert first.source_advisor_briefing == briefing
    assert ResearchRequest.objects.filter(
        source_advisor_briefing=briefing,
    ).count() == 1


@pytest.mark.django_db
def test_dispatch_failure_is_repaired(
    advisor_briefing,
    monkeypatch,
    settings,
):
    settings.AUTO_RESEARCH_AFTER_ADVISOR_ENABLED = True
    user, _, briefing = advisor_briefing
    calls = {"count": 0}

    def flaky_delay(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("broker unavailable")
        return SimpleNamespace(id="task-recovered")

    monkeypatch.setattr(
        "apps.research.tasks.generate_research_report_task.delay",
        flaky_delay,
    )

    failed, first_dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )
    failed.refresh_from_db()

    assert first_dispatched is False
    assert failed.status == ResearchRequest.Status.FAILED
    assert failed.error_code == "dispatch_failed"

    repaired, second_dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )
    repaired.refresh_from_db()

    assert second_dispatched is True
    assert repaired.id == failed.id
    assert repaired.status == ResearchRequest.Status.QUEUED
    assert repaired.error_code == ""
    assert repaired.celery_task_id == "task-recovered"


@pytest.mark.django_db
def test_active_manual_research_defers_automatic_handoff(
    advisor_briefing,
    monkeypatch,
    settings,
):
    settings.AUTO_RESEARCH_AFTER_ADVISOR_ENABLED = True
    user, profile, briefing = advisor_briefing
    active = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="Manual active request",
    )
    monkeypatch.setattr(
        "apps.research.tasks.generate_research_report_task.delay",
        lambda *args, **kwargs: SimpleNamespace(id="automatic-task"),
    )

    returned, dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )

    assert dispatched is False
    assert returned.id == active.id
    assert not ResearchRequest.objects.filter(
        source_advisor_briefing=briefing,
    ).exists()

    active.status = ResearchRequest.Status.SUCCEEDED
    active.completed_at = timezone.now()
    active.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    automatic, dispatched = queue_research_after_advisor(
        briefing=briefing,
        requested_by=user,
    )

    assert dispatched is True
    assert automatic.source_advisor_briefing == briefing
