from __future__ import annotations

import logging
from datetime import timedelta

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.knowledge.services import startup_profile_vector_scope
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
)
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
    "queue_timeout": (
        "The advisor generation job did not start in time. Please try again."
    ),
    "task_timeout": (
        "The advisor generation job exceeded its time limit. Please try again."
    ),
    "provider_unavailable": (
        "The local advisor model is temporarily unavailable."
    ),
    "provider_response_invalid": (
        "The advisor model returned an invalid response."
    ),
    "briefing_validation_failed": (
        "Generated guidance did not pass validation."
    ),
    "snapshot_changed": (
        "The source snapshot changed during generation."
    ),
    "unexpected_error": (
        "Advisor generation failed unexpectedly."
    ),
}


def _terminal_result(
    job: StartupAdvisorBriefingJob,
) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "status": job.status,
        "briefing_id": (
            str(job.briefing_id)
            if job.briefing_id
            else None
        ),
        "error_code": job.error_code,
    }


def _apply_failure(
    job: StartupAdvisorBriefingJob,
    *,
    error_code: str,
    completed_at,
) -> None:
    job.status = StartupAdvisorBriefingJob.Status.FAILED
    job.briefing = None
    job.error_code = error_code
    job.error_message = FAILURE_DETAILS[error_code]
    job.completed_at = completed_at


def _save_failed_job(
    job: StartupAdvisorBriefingJob,
) -> None:
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


def _mark_job_failed(
    *,
    job_id: str,
    error_code: str,
) -> StartupAdvisorBriefingJob:
    with transaction.atomic():
        job = StartupAdvisorBriefingJob.objects.select_for_update().get(
            pk=job_id,
        )

        if job.status in (
            StartupAdvisorBriefingJob.Status.SUCCEEDED,
            StartupAdvisorBriefingJob.Status.FAILED,
        ):
            return job

        _apply_failure(
            job,
            error_code=error_code,
            completed_at=timezone.now(),
        )
        _save_failed_job(job)
        return job


def _request_was_redelivered(task) -> bool:
    delivery_info = (
        getattr(task.request, "delivery_info", None)
        or {}
    )
    return bool(delivery_info.get("redelivered"))


def _ensure_auto_research_job_handoff(
    job_id: str,
) -> None:
    """Queue idempotent founder research from the advisor job itself."""
    try:
        from apps.research.services.advisor_trigger import (
            queue_research_after_advisor_job,
        )

        job = (
            StartupAdvisorBriefingJob.objects.select_related(
                "briefing",
                "requested_by",
                "startup_profile",
                "startup_profile__owner",
            ).get(pk=job_id)
        )

        if job.source_research_report_id is not None:
            logger.info(
                "Skipping advisor-to-research handoff for "
                "research-first advisor job %s.",
                job.id,
            )
            return

        research_request, dispatched = (
            queue_research_after_advisor_job(
                job=job,
                requested_by=job.requested_by,
            )
        )
        logger.info(
            "Advisor-job research handoff reconciled",
            extra={
                "advisor_briefing_job_id": str(job.id),
                "research_request_id": (
                    str(research_request.id)
                    if research_request is not None
                    else None
                ),
                "research_dispatched": dispatched,
            },
        )
    except Exception:
        logger.exception(
            "Advisor-job research handoff failed",
            extra={
                "advisor_briefing_job_id": str(job_id),
            },
        )


def _ensure_auto_research_handoff(
    briefing_id: str,
) -> None:
    """Link a successful briefing without changing advisor success."""
    try:
        from apps.research.services.advisor_trigger import (
            queue_research_after_advisor,
        )

        briefing = (
            StartupAdvisorBriefing.objects.select_related(
                "requested_by",
                "startup_profile",
            ).get(pk=briefing_id)
        )

        if briefing.source_research_report_id is not None:
            logger.info(
                "Skipping advisor-to-research handoff for "
                "research-first briefing %s.",
                briefing.id,
            )
            return

        research_request, dispatched = (
            queue_research_after_advisor(
                briefing=briefing,
                requested_by=briefing.requested_by,
            )
        )
        logger.info(
            "Advisor-to-research handoff reconciled",
            extra={
                "advisor_briefing_id": str(briefing.id),
                "research_request_id": (
                    str(research_request.id)
                    if research_request is not None
                    else None
                ),
                "research_dispatched": dispatched,
            },
        )
    except Exception:
        logger.exception(
            "Advisor-to-research handoff failed",
            extra={
                "advisor_briefing_id": str(briefing_id),
            },
        )


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=(
        settings.STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS
    ),
    time_limit=settings.STARTUP_ADVISOR_TASK_TIME_LIMIT_SECONDS,
)
def generate_startup_advisor_briefing_task(
    self,
    job_id: str,
) -> dict[str, object]:
    with transaction.atomic():
        job = (
            StartupAdvisorBriefingJob.objects.select_for_update()
            .get(pk=job_id)
        )

        if job.status in (
            StartupAdvisorBriefingJob.Status.SUCCEEDED,
            StartupAdvisorBriefingJob.Status.FAILED,
        ):
            handoff_job_id = str(job.id)
            transaction.on_commit(
                lambda: _ensure_auto_research_job_handoff(
                    handoff_job_id,
                )
            )
            if (
                job.status
                == StartupAdvisorBriefingJob.Status.SUCCEEDED
                and job.briefing_id
            ):
                briefing_id = str(job.briefing_id)
                transaction.on_commit(
                    lambda: _ensure_auto_research_handoff(
                        briefing_id,
                    )
                )
            return _terminal_result(job)

        now = timezone.now()

        if job.status == StartupAdvisorBriefingJob.Status.QUEUED:
            queue_cutoff = now - timedelta(
                seconds=(
                    settings.STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS
                ),
            )
            if job.created_at <= queue_cutoff:
                _apply_failure(
                    job,
                    error_code="queue_timeout",
                    completed_at=now,
                )
                _save_failed_job(job)
                handoff_job_id = str(job.id)
                transaction.on_commit(
                    lambda: _ensure_auto_research_job_handoff(
                        handoff_job_id,
                    )
                )
                return _terminal_result(job)

        if job.status == StartupAdvisorBriefingJob.Status.RUNNING:
            if not _request_was_redelivered(self):
                handoff_job_id = str(job.id)
                transaction.on_commit(
                    lambda: _ensure_auto_research_job_handoff(
                        handoff_job_id,
                    )
                )
                return _terminal_result(job)

            timeout_cutoff = now - timedelta(
                seconds=(
                    settings
                    .STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS
                ),
            )
            if (
                job.started_at is not None
                and job.started_at <= timeout_cutoff
            ):
                _apply_failure(
                    job,
                    error_code="task_timeout",
                    completed_at=now,
                )
                _save_failed_job(job)
                handoff_job_id = str(job.id)
                transaction.on_commit(
                    lambda: _ensure_auto_research_job_handoff(
                        handoff_job_id,
                    )
                )
                return _terminal_result(job)

        job.status = StartupAdvisorBriefingJob.Status.RUNNING
        job.started_at = now
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
        source_research_report = (
            job.source_research_report
            if job.source_research_report_id
            else None
        )
        handoff_job_id = str(job.id)
        transaction.on_commit(
            lambda: _ensure_auto_research_job_handoff(
                handoff_job_id,
            )
        )

    try:
        with startup_profile_vector_scope(
            str(source_snapshot.startup_profile_id),
        ):
            briefing = generate_startup_advisor_briefing(
                source_snapshot=source_snapshot,
                requested_by=requested_by,
                source_research_report=(
                    source_research_report
                ),
            )
    except SoftTimeLimitExceeded:
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="task_timeout",
        )
        return _terminal_result(failed_job)
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
            extra={
                "advisor_briefing_job_id": job_id,
            },
        )
        failed_job = _mark_job_failed(
            job_id=job_id,
            error_code="unexpected_error",
        )
        return _terminal_result(failed_job)

    with transaction.atomic():
        job = (
            StartupAdvisorBriefingJob.objects.select_for_update()
            .get(pk=job_id)
        )

        if job.status in (
            StartupAdvisorBriefingJob.Status.SUCCEEDED,
            StartupAdvisorBriefingJob.Status.FAILED,
        ):
            handoff_job_id = str(job.id)
            transaction.on_commit(
                lambda: _ensure_auto_research_job_handoff(
                    handoff_job_id,
                )
            )
            if (
                job.status
                == StartupAdvisorBriefingJob.Status.SUCCEEDED
                and job.briefing_id
            ):
                briefing_id = str(job.briefing_id)
                transaction.on_commit(
                    lambda: _ensure_auto_research_handoff(
                        briefing_id,
                    )
                )
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

        handoff_job_id = str(job.id)
        briefing_id = str(briefing.id)
        transaction.on_commit(
            lambda: _ensure_auto_research_job_handoff(
                handoff_job_id,
            )
        )
        transaction.on_commit(
            lambda: _ensure_auto_research_handoff(
                briefing_id,
            )
        )

    return _terminal_result(job)
