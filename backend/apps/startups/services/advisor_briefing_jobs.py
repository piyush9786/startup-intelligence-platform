from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.startups.models import (
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupProfile,
)

ACTIVE_JOB_STATUSES = (
    StartupAdvisorBriefingJob.Status.QUEUED,
    StartupAdvisorBriefingJob.Status.RUNNING,
)

DISPATCH_FAILURE_MESSAGE = "The advisor generation job could not be submitted to the worker."

STALE_FAILURE_DETAILS = {
    "queue_timeout": ("The advisor generation job did not start in time. Please try again."),
    "worker_interrupted": (
        "The advisor generation worker stopped before completing the job. Please try again."
    ),
}


class AdvisorBriefingJobDispatchError(RuntimeError):
    pass


def _stale_failure_code(
    job: StartupAdvisorBriefingJob,
    *,
    now,
) -> str:
    if job.status == StartupAdvisorBriefingJob.Status.QUEUED:
        queue_cutoff = now - timedelta(
            seconds=settings.STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS,
        )
        if job.created_at <= queue_cutoff:
            return "queue_timeout"

    if job.status == StartupAdvisorBriefingJob.Status.RUNNING and job.started_at is not None:
        running_cutoff = now - timedelta(
            seconds=settings.STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS,
        )
        if job.started_at <= running_cutoff:
            return "worker_interrupted"

    return ""


def _mark_locked_job_failed(
    job: StartupAdvisorBriefingJob,
    *,
    error_code: str,
    error_message: str,
    completed_at,
) -> StartupAdvisorBriefingJob:
    job.status = StartupAdvisorBriefingJob.Status.FAILED
    job.briefing = None
    job.error_code = error_code
    job.error_message = error_message
    job.completed_at = completed_at
    job.save(
        update_fields=[
            "status",
            "briefing",
            "error_code",
            "error_message",
            "completed_at",
            "updated_at",
        ],
    )
    return job


def reconcile_startup_advisor_briefing_job(
    *,
    job_id,
    now=None,
) -> StartupAdvisorBriefingJob:
    """Mark a stale active job failed and return its current state."""

    effective_now = now or timezone.now()

    with transaction.atomic():
        job = StartupAdvisorBriefingJob.objects.select_for_update().get(
            pk=job_id,
        )
        error_code = _stale_failure_code(
            job,
            now=effective_now,
        )

        if error_code:
            _mark_locked_job_failed(
                job,
                error_code=error_code,
                error_message=STALE_FAILURE_DETAILS[error_code],
                completed_at=effective_now,
            )

        return job


def queue_startup_advisor_briefing_job(
    *,
    source_snapshot: StartupAdvisorSnapshot,
    requested_by: Any,
    source_research_report: Any | None = None,
) -> tuple[StartupAdvisorBriefingJob, bool]:
    """Create and dispatch one non-stale active job per startup profile."""

    with transaction.atomic():
        StartupProfile.objects.select_for_update().only("id").get(
            pk=source_snapshot.startup_profile_id,
        )

        if (
            source_research_report is not None
            and source_research_report.startup_profile_id
            != source_snapshot.startup_profile_id
        ):
            raise ValueError(
                "The research report and advisor snapshot must "
                "belong to the same startup profile."
            )

        if source_research_report is not None:
            existing_for_report = (
                StartupAdvisorBriefingJob.objects
                .select_for_update()
                .filter(
                    source_research_report=(
                        source_research_report
                    ),
                )
                .first()
            )
            if existing_for_report is not None:
                return existing_for_report, False

        existing_job = (
            StartupAdvisorBriefingJob.objects.select_for_update()
            .filter(
                startup_profile_id=source_snapshot.startup_profile_id,
                status__in=ACTIVE_JOB_STATUSES,
            )
            .order_by("-created_at", "-id")
            .first()
        )

        if existing_job is not None:
            error_code = _stale_failure_code(
                existing_job,
                now=timezone.now(),
            )

            if not error_code:
                if (
                    source_research_report is not None
                    and existing_job.source_research_report_id
                    != source_research_report.id
                ):
                    raise AdvisorBriefingJobDispatchError(
                        "Another advisor generation job is "
                        "already active for this startup profile."
                    )

                return existing_job, False

            _mark_locked_job_failed(
                existing_job,
                error_code=error_code,
                error_message=STALE_FAILURE_DETAILS[error_code],
                completed_at=timezone.now(),
            )

        job = StartupAdvisorBriefingJob.objects.create(
            requested_by=requested_by,
            startup_profile_id=source_snapshot.startup_profile_id,
            source_snapshot=source_snapshot,
            source_research_report=source_research_report,
        )

    try:
        from apps.startups.tasks import (
            generate_startup_advisor_briefing_task,
        )

        async_result = generate_startup_advisor_briefing_task.delay(
            str(job.id),
        )
    except Exception as exc:
        StartupAdvisorBriefingJob.objects.filter(
            pk=job.pk,
            status=StartupAdvisorBriefingJob.Status.QUEUED,
        ).update(
            status=StartupAdvisorBriefingJob.Status.FAILED,
            error_code="dispatch_failed",
            error_message=DISPATCH_FAILURE_MESSAGE,
            completed_at=timezone.now(),
        )
        job.refresh_from_db()
        raise AdvisorBriefingJobDispatchError(
            DISPATCH_FAILURE_MESSAGE,
        ) from exc

    celery_task_id = str(async_result.id or "")
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        celery_task_id=celery_task_id,
    )
    job.celery_task_id = celery_task_id

    return job, True
