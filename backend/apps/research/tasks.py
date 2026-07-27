"""Celery background tasks for research app."""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from .services.report_generator import generate_research_report

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=540,
    time_limit=600,
)
def generate_research_report_task(
    self,
    research_request_id: str,
) -> dict[str, Any]:
    """Execute research report generation asynchronously."""
    logger.info("Starting generate_research_report_task for request %s", research_request_id)
    report = generate_research_report(research_request_id)
    return {
        "research_request_id": research_request_id,
        "report_id": str(report.id),
        "status": "succeeded",
    }
