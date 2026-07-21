from __future__ import annotations

from typing import Any

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


class AdvisorBriefingJobDispatchError(RuntimeError):
    pass


def queue_startup_advisor_briefing_job(
    *,
    source_snapshot: StartupAdvisorSnapshot,
    requested_by: Any,
) -> tuple[StartupAdvisorBriefingJob, bool]:
    """Create and dispatch one active briefing job per startup profile."""

    with transaction.atomic():
        StartupProfile.objects.select_for_update().only("id").get(
            pk=source_snapshot.startup_profile_id,
        )

        existing_job = (
            StartupAdvisorBriefingJob.objects.filter(
                startup_profile_id=source_snapshot.startup_profile_id,
                status__in=ACTIVE_JOB_STATUSES,
            )
            .select_related(
                "startup_profile",
                "source_snapshot",
                "briefing",
                "requested_by",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if existing_job is not None:
            return existing_job, False

        job = StartupAdvisorBriefingJob.objects.create(
            requested_by=requested_by,
            startup_profile_id=source_snapshot.startup_profile_id,
            source_snapshot=source_snapshot,
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
