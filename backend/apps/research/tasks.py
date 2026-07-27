"""Thin Celery execution wrappers for research workflows."""
from __future__ import annotations

import logging
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.conf import settings

from .services.job_state import (
    mark_research_failed,
    recover_stale_research_requests,
)
from .services.report_generator import generate_research_report

logger = logging.getLogger(__name__)


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

    report.research_request.refresh_from_db(
        fields=["status"],
    )
    return {
        "research_request_id": research_request_id,
        "report_id": str(report.id),
        "status": report.research_request.status,
    }


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
