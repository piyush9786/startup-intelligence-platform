"""Thin Celery execution wrappers for research workflows."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.research.models import ResearchRequest
from apps.startups.models import StartupAdvisorBriefingJob

from .services.job_state import (
    mark_research_failed,
    recover_stale_research_requests,
)
from .services.report_generator import generate_research_report

logger = logging.getLogger(__name__)


def _queue_advisor_after_research(report):
    request = (
        ResearchRequest.objects
        .select_related(
            "advisor_snapshot",
            "requested_by",
        )
        .get(pk=report.research_request_id)
    )

    if (
        request.workflow_type
        != ResearchRequest.WorkflowType.RESEARCH_FIRST_INTELLIGENCE
    ):
        return None, False, "not_requested"

    if request.advisor_snapshot_id is None:
        logger.error(
            "Research-first request %s has no advisor snapshot.",
            request.id,
        )
        return None, False, "missing_snapshot"

    from apps.startups.services.advisor_briefing_jobs import (
        queue_startup_advisor_briefing_job,
    )

    job, created = queue_startup_advisor_briefing_job(
        source_snapshot=request.advisor_snapshot,
        requested_by=request.requested_by,
        source_research_report=report,
    )

    return job, created, "queued"


@shared_task(
    bind=True,
    name="apps.research.tasks.generate_research_report_task",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=(
        settings.RESEARCH_TASK_SOFT_TIME_LIMIT_SECONDS
    ),
    time_limit=settings.RESEARCH_TASK_TIME_LIMIT_SECONDS,
)
def generate_research_report_task(
    self,
    research_request_id: str,
) -> dict[str, Any]:
    """Execute the Python orchestrator in a durable worker."""
    task_id = str(self.request.id or "")
    logger.info(
        "Starting research request %s with task %s",
        research_request_id,
        task_id,
    )

    try:
        report = generate_research_report(
            research_request_id,
            task_id=task_id,
        )
    except SoftTimeLimitExceeded:
        mark_research_failed(
            research_request_id,
            error_code="task_timeout",
            error_message=(
                "Research generation exceeded its allowed "
                "execution time."
            ),
            overwrite_failed=True,
        )
        logger.exception(
            "Research request %s exceeded the soft time limit",
            research_request_id,
        )
        raise

    research_request = (
        ResearchRequest.objects
        .select_related(
            "advisor_snapshot",
            "requested_by",
        )
        .get(pk=report.research_request_id)
    )

    advisor_job = None
    advisor_created = False
    advisor_handoff_status = "not_requested"

    try:
        (
            advisor_job,
            advisor_created,
            advisor_handoff_status,
        ) = _queue_advisor_after_research(report)
    except Exception:
        advisor_handoff_status = "dispatch_failed"
        logger.exception(
            "Research-to-advisor handoff failed for report %s.",
            report.id,
        )

    return {
        "research_request_id": research_request_id,
        "report_id": str(report.id),
        "status": research_request.status,
        "advisor_job_id": (
            str(advisor_job.id)
            if advisor_job is not None
            else None
        ),
        "advisor_job_created": advisor_created,
        "advisor_handoff_status": advisor_handoff_status,
    }


@shared_task(
    name="research.reconcile_advisor_handoffs",
    ignore_result=True,
)
def reconcile_advisor_research_handoffs_task() -> int:
    """Repair advisor jobs whose automatic research was not dispatched."""
    if not getattr(
        settings,
        "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED",
        True,
    ):
        return 0

    from apps.research.services.advisor_trigger import (
        RECOVERABLE_AUTO_RESEARCH_ERRORS,
        queue_research_after_advisor_job,
    )

    batch_size = max(
        1,
        int(
            getattr(
                settings,
                "AUTO_RESEARCH_HANDOFF_RECONCILE_BATCH_SIZE",
                50,
            )
        ),
    )
    max_age_seconds = max(
        300,
        int(
            getattr(
                settings,
                "AUTO_RESEARCH_HANDOFF_RECONCILE_MAX_AGE_SECONDS",
                7200,
            )
        ),
    )
    created_after = timezone.now() - timedelta(
        seconds=max_age_seconds,
    )

    jobs = list(
        StartupAdvisorBriefingJob.objects.filter(
            Q(requested_by__isnull=False)
            | Q(startup_profile__owner__isnull=False)
        )
        .filter(
            source_research_report__isnull=True,
            created_at__gte=created_after,
        )
        .filter(
            Q(automatic_research_request__isnull=True)
            | Q(
                automatic_research_request__status=(
                    ResearchRequest.Status.FAILED
                ),
                automatic_research_request__error_code__in=(
                    RECOVERABLE_AUTO_RESEARCH_ERRORS
                ),
            )
            | Q(
                automatic_research_request__status=(
                    ResearchRequest.Status.QUEUED
                ),
                automatic_research_request__celery_task_id="",
            )
        )
        .select_related(
            "briefing",
            "requested_by",
            "startup_profile",
            "startup_profile__owner",
        )
        .order_by("created_at", "id")[:batch_size]
    )

    dispatched = 0
    for job in jobs:
        _, created_or_redispatched = queue_research_after_advisor_job(
            job=job,
            requested_by=job.requested_by,
        )
        if created_or_redispatched:
            dispatched += 1

    if dispatched:
        logger.info(
            "Reconciled %s advisor-job research handoff(s).",
            dispatched,
        )
    return dispatched


@shared_task(
    name="research.recover_stale_requests",
    ignore_result=True,
)
def recover_stale_research_requests_task() -> int:
    """Release startup profiles blocked by abandoned jobs."""
    recovered = recover_stale_research_requests()
    if recovered:
        logger.warning(
            "Recovered %s stale research request(s)",
            recovered,
        )
    return recovered
