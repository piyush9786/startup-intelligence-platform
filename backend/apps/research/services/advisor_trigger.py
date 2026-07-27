"""Queue one founder-research job after advisor generation."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.research.models import ResearchRequest
from apps.startups.models import StartupAdvisorBriefing, StartupProfile

logger = logging.getLogger(__name__)

AUTO_RESEARCH_QUESTION = (
    "Create a comprehensive founder research report for this startup. "
    "Analyze current competitors, recent market developments, verified "
    "government schemes, compliance and certification requirements, "
    "funding opportunities, loans and credit support, historical peers, "
    "risks, market gaps, capital scenarios, and recommended next actions."
)

ACTIVE_STATUSES = (
    ResearchRequest.Status.QUEUED,
    ResearchRequest.Status.RUNNING,
)


def queue_research_after_advisor(
    *,
    briefing: StartupAdvisorBriefing,
    requested_by: Any,
) -> tuple[ResearchRequest | None, bool]:
    """Create and dispatch at most one research request per briefing."""
    if not getattr(settings, "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED", True):
        return None, False

    actor = requested_by or briefing.requested_by
    if actor is None:
        logger.warning(
            "Advisor briefing %s has no requesting user; research skipped.",
            briefing.pk,
        )
        return None, False

    with transaction.atomic():
        StartupProfile.objects.select_for_update().only("id").get(
            pk=briefing.startup_profile_id,
        )

        existing = (
            ResearchRequest.objects.select_for_update()
            .filter(source_advisor_briefing=briefing)
            .first()
        )
        if existing is not None:
            return existing, False

        active = (
            ResearchRequest.objects.select_for_update()
            .filter(
                startup_profile_id=briefing.startup_profile_id,
                status__in=ACTIVE_STATUSES,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if active is not None:
            logger.info(
                "Research request %s is already active for profile %s.",
                active.pk,
                briefing.startup_profile_id,
            )
            return active, False

        try:
            research_request = ResearchRequest.objects.create(
                startup_profile_id=briefing.startup_profile_id,
                requested_by=actor,
                source_advisor_briefing=briefing,
                question=AUTO_RESEARCH_QUESTION,
            )
        except IntegrityError:
            existing = ResearchRequest.objects.filter(
                source_advisor_briefing=briefing,
            ).first()
            if existing is not None:
                return existing, False
            active = ResearchRequest.objects.filter(
                startup_profile_id=briefing.startup_profile_id,
                status__in=ACTIVE_STATUSES,
            ).first()
            if active is not None:
                return active, False
            raise

    try:
        from apps.research.tasks import generate_research_report_task

        result = generate_research_report_task.delay(str(research_request.id))
    except Exception:
        ResearchRequest.objects.filter(
            pk=research_request.pk,
            status=ResearchRequest.Status.QUEUED,
        ).update(
            status=ResearchRequest.Status.FAILED,
            completed_at=timezone.now(),
            error_code="dispatch_failed",
            error_message=(
                "Automatic founder research could not be submitted to the worker."
            ),
        )
        research_request.refresh_from_db()
        logger.exception(
            "Automatic research dispatch failed for briefing %s.",
            briefing.pk,
        )
        return research_request, False

    task_id = str(result.id or "")
    ResearchRequest.objects.filter(pk=research_request.pk).update(
        celery_task_id=task_id,
    )
    research_request.celery_task_id = task_id
    return research_request, True
