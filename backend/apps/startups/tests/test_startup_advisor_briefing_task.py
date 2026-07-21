from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.startups.models import StartupAdvisorBriefingJob
from apps.startups.services.advisor_briefing_jobs import (
    AdvisorBriefingJobDispatchError,
    queue_startup_advisor_briefing_job,
)
from apps.startups.services.llm_provider import (
    LLMProviderUnavailableError,
)
from apps.startups.tasks import (
    generate_startup_advisor_briefing_task,
)
from apps.startups.tests.test_startup_advisor_briefing_retrieval_api import (
    create_briefing,
    create_source,
)

pytestmark = pytest.mark.django_db


def test_queue_creates_and_dispatches_job(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-job-queue",
    )
    dispatched_job_ids = []

    def fake_delay(job_id):
        dispatched_job_ids.append(job_id)
        return SimpleNamespace(id="celery-job-queue")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        fake_delay,
    )

    job, created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    assert created is True
    assert job.startup_profile_id == profile.id
    assert job.source_snapshot_id == snapshot.id
    assert job.status == StartupAdvisorBriefingJob.Status.QUEUED
    assert job.celery_task_id == "celery-job-queue"
    assert dispatched_job_ids == [str(job.id)]


def test_queue_reuses_existing_active_job(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-reuse",
    )
    dispatch_count = 0

    def fake_delay(_job_id):
        nonlocal dispatch_count
        dispatch_count += 1
        return SimpleNamespace(id="celery-job-reuse")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        fake_delay,
    )

    first_job, first_created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    second_job, second_created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    assert first_created is True
    assert second_created is False
    assert second_job.id == first_job.id
    assert dispatch_count == 1


def test_dispatch_failure_marks_job_failed(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-job-dispatch-failure",
    )

    def failing_delay(_job_id):
        raise OSError("broker detail must remain private")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        failing_delay,
    )

    with pytest.raises(AdvisorBriefingJobDispatchError):
        queue_startup_advisor_briefing_job(
            source_snapshot=snapshot,
            requested_by=owner,
        )

    job = StartupAdvisorBriefingJob.objects.get(
        startup_profile=profile,
    )
    assert job.status == StartupAdvisorBriefingJob.Status.FAILED
    assert job.error_code == "dispatch_failed"
    assert job.completed_at is not None
    assert "broker detail" not in job.error_message


def test_task_persists_successful_briefing(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-job-success",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(id="celery-job-success"),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="async-success",
        completed_at=timezone.now(),
    )

    generation_calls = 0

    def fake_generation(**_kwargs):
        nonlocal generation_calls
        generation_calls += 1
        return briefing

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        fake_generation,
    )

    result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    job.refresh_from_db()

    assert generation_calls == 1
    assert result["status"] == "succeeded"
    assert result["briefing_id"] == str(briefing.id)
    assert job.status == StartupAdvisorBriefingJob.Status.SUCCEEDED
    assert job.briefing_id == briefing.id
    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.error_code == ""


def test_task_records_safe_provider_failure(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-provider-failure",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(
            id="celery-job-provider-failure",
        ),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    def failing_generation(**_kwargs):
        raise LLMProviderUnavailableError(
            "private infrastructure detail",
        )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        failing_generation,
    )

    result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    job.refresh_from_db()

    assert result == {
        "job_id": str(job.id),
        "status": "failed",
        "briefing_id": None,
        "error_code": "provider_unavailable",
    }
    assert job.status == StartupAdvisorBriefingJob.Status.FAILED
    assert job.error_code == "provider_unavailable"
    assert job.started_at is not None
    assert job.completed_at is not None
    assert "private infrastructure detail" not in job.error_message


def test_completed_task_is_idempotent(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-job-idempotent",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(
            id="celery-job-idempotent",
        ),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="async-idempotent",
        completed_at=timezone.now(),
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        lambda **_kwargs: briefing,
    )

    first_result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    def unexpected_generation(**_kwargs):
        raise AssertionError(
            "A succeeded job must not generate another briefing.",
        )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        unexpected_generation,
    )

    second_result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    assert first_result == second_result
    assert second_result["status"] == "succeeded"
    assert second_result["briefing_id"] == str(briefing.id)
