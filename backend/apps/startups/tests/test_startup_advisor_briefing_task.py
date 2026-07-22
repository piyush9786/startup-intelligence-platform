from datetime import timedelta
from types import SimpleNamespace

import pytest
from billiard.exceptions import SoftTimeLimitExceeded
from django.conf import settings
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


def test_queue_replaces_stale_queued_job(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-stale-queued",
    )
    dispatched_job_ids = []

    def fake_delay(job_id):
        dispatched_job_ids.append(job_id)
        return SimpleNamespace(
            id=f"celery-{len(dispatched_job_ids)}",
        )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        fake_delay,
    )

    stale_job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    StartupAdvisorBriefingJob.objects.filter(
        pk=stale_job.pk,
    ).update(
        created_at=(
            timezone.now()
            - timedelta(
                seconds=(settings.STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS + 1),
            )
        ),
    )

    replacement, created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    stale_job.refresh_from_db()

    assert created is True
    assert replacement.id != stale_job.id
    assert stale_job.status == "failed"
    assert stale_job.error_code == "queue_timeout"
    assert stale_job.completed_at is not None
    assert dispatched_job_ids == [
        str(stale_job.id),
        str(replacement.id),
    ]


def test_queue_replaces_stale_running_job(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-stale-running",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda job_id: SimpleNamespace(
            id=f"celery-{job_id}",
        ),
    )

    stale_job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    StartupAdvisorBriefingJob.objects.filter(
        pk=stale_job.pk,
    ).update(
        status=StartupAdvisorBriefingJob.Status.RUNNING,
        started_at=(
            timezone.now()
            - timedelta(
                seconds=(settings.STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS + 1),
            )
        ),
    )

    replacement, created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    stale_job.refresh_from_db()

    assert created is True
    assert replacement.id != stale_job.id
    assert stale_job.status == "failed"
    assert stale_job.error_code == "worker_interrupted"
    assert stale_job.completed_at is not None


def test_task_records_soft_timeout_failure(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-soft-timeout",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(
            id="celery-soft-timeout",
        ),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )

    def timed_out_generation(**_kwargs):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        timed_out_generation,
    )

    result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    job.refresh_from_db()

    assert result["status"] == "failed"
    assert result["error_code"] == "task_timeout"
    assert job.status == "failed"
    assert job.error_code == "task_timeout"
    assert job.completed_at is not None


def test_redelivered_task_reclaims_running_job(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-job-redelivery",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(
            id="celery-redelivery",
        ),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    original_started_at = timezone.now() - timedelta(minutes=2)
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        status=StartupAdvisorBriefingJob.Status.RUNNING,
        started_at=original_started_at,
    )

    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="redelivered-success",
        completed_at=timezone.now(),
    )

    monkeypatch.setattr(
        "apps.startups.tasks._request_was_redelivered",
        lambda _task: True,
    )
    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        lambda **_kwargs: briefing,
    )

    result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    job.refresh_from_db()

    assert result["status"] == "succeeded"
    assert job.status == "succeeded"
    assert job.briefing_id == briefing.id
    assert job.started_at > original_started_at


def test_late_redelivery_becomes_task_timeout(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-job-late-redelivery",
    )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        lambda _job_id: SimpleNamespace(
            id="celery-late-redelivery",
        ),
    )

    job, _created = queue_startup_advisor_briefing_job(
        source_snapshot=snapshot,
        requested_by=owner,
    )
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        status=StartupAdvisorBriefingJob.Status.RUNNING,
        started_at=(
            timezone.now()
            - timedelta(
                seconds=(settings.STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS + 1),
            )
        ),
    )

    monkeypatch.setattr(
        "apps.startups.tasks._request_was_redelivered",
        lambda _task: True,
    )

    def unexpected_generation(**_kwargs):
        raise AssertionError(
            "An expired redelivery must not invoke generation.",
        )

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing",
        unexpected_generation,
    )

    result = generate_startup_advisor_briefing_task.run(
        str(job.id),
    )

    job.refresh_from_db()

    assert result["status"] == "failed"
    assert result["error_code"] == "task_timeout"
    assert job.status == "failed"
    assert job.error_code == "task_timeout"
