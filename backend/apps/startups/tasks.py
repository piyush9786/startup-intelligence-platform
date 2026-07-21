from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.startups.models import StartupAdvisorBriefingJob
from apps.startups.services.advisor_briefing import (
    AdvisorSnapshotChangedError,
    generate_startup_advisor_briefing,
)
from apps.startups.services.briefing_schema import (
    BriefingOutputValidationError,
)
from apps.startups.services.llm_provider import (
    LLMProviderResponseError,
    LLMProviderUnavailableError,
)

logger = logging.getLogger(__name__)

FAILURE_DETAILS = {
    "provider_unavailable": ("The local advisor model is temporarily unavailable."),
    "provider_response_invalid": ("The advisor model returned an invalid response."),
    "briefing_validation_failed": ("Generated guidance did not pass validation."),
    "snapshot_changed": ("The source snapshot changed during generation."),
    "unexpected_error": ("Advisor generation failed unexpectedly."),
}


def _terminal_result(
    job: StartupAdvisorBriefingJob,
) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "status": job.status,
        "briefing_id": (str(job.briefing_id) if job.briefing_id else None),
        "error_code": job.error_code,
    }


def _mark_job_failed(
    *,
    job_id: str,
    error_code: str,
) -> StartupAdvisorBriefingJob:
    with transaction.atomic():
        job = StartupAdvisorBriefingJob.objects.select_for_update().get(pk=job_id)

        if job.status == StartupAdvisorBriefingJob.Status.SUCCEEDED:
            return job

        job.status = StartupAdvisorBriefingJob.Status.FAILED
        job.briefing = None
        job.error_code = error_code
        job.error_message = FAILURE_DETAILS[error_code]
        job.completed_at = timezone.now()
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


@shared_task(bind=True)
def generate_startup_advisor_briefing_task(
    self,
    job_id: str,
) -> dict[str, object]:
    with transaction.atomic():
        job = StartupAdvisorBriefingJob.objects.select_for_update().get(
            pk=job_id,
        )

        if job.status in (
            StartupAdvisorBriefingJob.Status.SUCCEEDED,
            StartupAdvisorBriefingJob.Status.FAILED,
        ):
            return _terminal_result(job)

        if job.status == StartupAdvisorBriefingJob.Status.RUNNING:
            return _terminal_result(job)

        job.status = StartupAdvisorBriefingJob.Status.RUNNING
        job.started_at = timezone.now()
        job.error_code = ""
        job.error_message = ""

        task_id = getattr(self.request, "id", None)
        if task_id:
            job.celery_task_id = str(task_id)

        job.save(
            update_fields=[
                "status",
                "started_at",
                "error_code",
                "error_message",
                "celery_task_id",
                "updated_at",
            ],
        )

        source_snapshot = job.source_snapshot
        requested_by = job.requested_by

    try:
        briefing = generate_startup_advisor_briefing(
            source_snapshot=source_snapshot,
            requested_by=requested_by,
        )
    except LLMProviderUnavailableError:
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="provider_unavailable",
        )
        return _terminal_result(failed_job)
    except LLMProviderResponseError:
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="provider_response_invalid",
        )
        return _terminal_result(failed_job)
    except BriefingOutputValidationError:
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="briefing_validation_failed",
        )
        return _terminal_result(failed_job)
    except AdvisorSnapshotChangedError:
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="snapshot_changed",
        )
        return _terminal_result(failed_job)
    except Exception:
        logger.exception(
            "Unexpected startup advisor briefing job failure",
            extra={"advisor_briefing_job_id": job_id},
        )
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="unexpected_error",
        )
        return _terminal_result(failed_job)

    with transaction.atomic():
        job = StartupAdvisorBriefingJob.objects.select_for_update().get(pk=job_id)

        if job.status == StartupAdvisorBriefingJob.Status.SUCCEEDED:
            return _terminal_result(job)

        job.status = StartupAdvisorBriefingJob.Status.SUCCEEDED
        job.briefing = briefing
        job.error_code = ""
        job.error_message = ""
        job.completed_at = timezone.now()
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

    return _terminal_result(job)
