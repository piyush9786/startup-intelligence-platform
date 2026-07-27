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


def _mark_dispatch_failed(
    research_request: ResearchRequest,
) -> ResearchRequest:
    ResearchRequest.objects.filter(
        pk=research_request.pk,
        status=ResearchRequest.Status.QUEUED,
    ).update(
        status=ResearchRequest.Status.FAILED,
        completed_at=timezone.now(),
        error_code="dispatch_failed",
        error_message=(
            "Automatic founder research could not be submitted "
            "to the worker."
        ),
    )
    research_request.refresh_from_db()
    return research_request


def _dispatch_research(
    research_request: ResearchRequest,
) -> tuple[ResearchRequest, bool]:
    try:
        from apps.research.tasks import generate_research_report_task

        result = generate_research_report_task.delay(
            str(research_request.id),
        )
    except Exception:
        research_request = _mark_dispatch_failed(research_request)
        logger.exception(
            "Automatic research dispatch failed for request %s.",
            research_request.pk,
        )
        return research_request, False

    task_id = str(result.id or "")
    ResearchRequest.objects.filter(
        pk=research_request.pk,
    ).update(celery_task_id=task_id)
    research_request.celery_task_id = task_id
    return research_request, True


def queue_research_after_advisor(
    *,
    briefing: StartupAdvisorBriefing,
    requested_by: Any,
) -> tuple[ResearchRequest | None, bool]:
    """Create or repair one automatic request for an advisor briefing.

    The operation is idempotent. A request whose only failure was broker
    dispatch is reset and dispatched again. If another request is active for
    the same profile, no duplicate request is created; the periodic
    reconciliation task will try this briefing again later.
    """
    if not getattr(
        settings,
        "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED",
        True,
    ):
        return None, False

    actor = requested_by or briefing.requested_by
    if actor is None:
        logger.warning(
            "Advisor briefing %s has no requesting user; research skipped.",
            briefing.pk,
        )
        return None, False

    research_request: ResearchRequest | None = None

    try:
        with transaction.atomic():
            StartupProfile.objects.select_for_update().only("id").get(
                pk=briefing.startup_profile_id,
            )

            existing = (
                ResearchRequest.objects.select_for_update()
                .filter(source_advisor_briefing=briefing)
                .first()
            )

            active_query = ResearchRequest.objects.select_for_update().filter(
                startup_profile_id=briefing.startup_profile_id,
                status__in=ACTIVE_STATUSES,
            )
            if existing is not None:
                active_query = active_query.exclude(pk=existing.pk)

            active = active_query.order_by(
                "-created_at",
                "-id",
            ).first()
            if active is not None:
                logger.info(
                    "Automatic research for briefing %s is waiting for "
                    "active request %s.",
                    briefing.pk,
                    active.pk,
                )
                return active, False

            if existing is not None:
                if (
                    existing.status == ResearchRequest.Status.FAILED
                    and existing.error_code == "dispatch_failed"
                ):
                    existing.status = ResearchRequest.Status.QUEUED
                    existing.started_at = None
                    existing.completed_at = None
                    existing.error_code = ""
                    existing.error_message = ""
                    existing.celery_task_id = ""
                    existing.save(
                        update_fields=[
                            "status",
                            "started_at",
                            "completed_at",
                            "error_code",
                            "error_message",
                            "celery_task_id",
                            "updated_at",
                        ]
                    )
                    research_request = existing
                else:
                    return existing, False
            else:
                research_request = ResearchRequest.objects.create(
                    startup_profile_id=briefing.startup_profile_id,
                    requested_by=actor,
                    source_advisor_briefing=briefing,
                    question=AUTO_RESEARCH_QUESTION,
                )
    except IntegrityError:
        active = ResearchRequest.objects.filter(
            startup_profile_id=briefing.startup_profile_id,
            status__in=ACTIVE_STATUSES,
        ).first()
        if active is not None:
            return active, False

        existing = ResearchRequest.objects.filter(
            source_advisor_briefing=briefing,
        ).first()
        if existing is not None:
            return existing, False
        raise

    if research_request is None:
        return None, False

    return _dispatch_research(research_request)
