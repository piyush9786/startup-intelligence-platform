"""Queue one founder-research job when advisor generation is triggered."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.research.models import ResearchRequest
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupProfile,
)

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

RECOVERABLE_AUTO_RESEARCH_ERRORS = frozenset(
    {
        "dispatch_failed",
        "queue_timeout",
        "worker_interrupted",
    }
)


def _resolve_actor(
    *,
    profile: StartupProfile,
    requested_by: Any,
    job: StartupAdvisorBriefingJob | None = None,
    briefing: StartupAdvisorBriefing | None = None,
) -> Any:
    return (
        requested_by
        or (job.requested_by if job is not None else None)
        or (briefing.requested_by if briefing is not None else None)
        or profile.owner
    )


def _needs_handoff_repair(
    research_request: ResearchRequest,
) -> bool:
    if (
        research_request.status == ResearchRequest.Status.QUEUED
        and not research_request.celery_task_id
    ):
        return True
    return (
        research_request.status == ResearchRequest.Status.FAILED
        and research_request.error_code
        in RECOVERABLE_AUTO_RESEARCH_ERRORS
    )


def _reset_for_redispatch(
    research_request: ResearchRequest,
) -> ResearchRequest:
    research_request.status = ResearchRequest.Status.QUEUED
    research_request.started_at = None
    research_request.completed_at = None
    research_request.error_code = ""
    research_request.error_message = ""
    research_request.celery_task_id = ""
    research_request.save(
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
    return research_request


def _link_sources(
    research_request: ResearchRequest,
    *,
    job: StartupAdvisorBriefingJob | None,
    briefing: StartupAdvisorBriefing | None,
) -> ResearchRequest:
    update_fields: list[str] = []

    if job is not None and research_request.source_advisor_job_id is None:
        research_request.source_advisor_job = job
        update_fields.append("source_advisor_job")

    if (
        briefing is not None
        and research_request.source_advisor_briefing_id is None
    ):
        research_request.source_advisor_briefing = briefing
        update_fields.append("source_advisor_briefing")

    if update_fields:
        research_request.save(
            update_fields=[*update_fields, "updated_at"],
        )

    return research_request


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


def _existing_for_source(
    *,
    job: StartupAdvisorBriefingJob | None,
    briefing: StartupAdvisorBriefing | None,
) -> ResearchRequest | None:
    if job is not None:
        existing = ResearchRequest.objects.filter(
            source_advisor_job=job,
        ).first()
        if existing is not None:
            return existing

    if briefing is not None:
        return ResearchRequest.objects.filter(
            source_advisor_briefing=briefing,
        ).first()

    return None


def _queue_automatic_research(
    *,
    startup_profile_id: Any,
    requested_by: Any,
    job: StartupAdvisorBriefingJob | None = None,
    briefing: StartupAdvisorBriefing | None = None,
) -> tuple[ResearchRequest | None, bool]:
    if not getattr(
        settings,
        "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED",
        True,
    ):
        return None, False

    research_request: ResearchRequest | None = None

    try:
        with transaction.atomic():
            profile = (
                StartupProfile.objects.select_for_update()
                .select_related("owner")
                .get(pk=startup_profile_id)
            )
            actor = _resolve_actor(
                profile=profile,
                requested_by=requested_by,
                job=job,
                briefing=briefing,
            )
            if actor is None:
                logger.warning(
                    "Advisor research handoff for profile %s has no actor; "
                    "research skipped.",
                    profile.pk,
                )
                return None, False

            existing = _existing_for_source(
                job=job,
                briefing=briefing,
            )
            if existing is not None:
                existing = _link_sources(
                    existing,
                    job=job,
                    briefing=briefing,
                )

            active_query = ResearchRequest.objects.select_for_update().filter(
                startup_profile=profile,
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
                    "Automatic research for advisor source is waiting for "
                    "active request %s on profile %s.",
                    active.pk,
                    profile.pk,
                )
                return active, False

            if existing is not None:
                if _needs_handoff_repair(existing):
                    research_request = _reset_for_redispatch(existing)
                else:
                    return existing, False
            else:
                research_request = ResearchRequest.objects.create(
                    startup_profile=profile,
                    requested_by=actor,
                    source_advisor_job=job,
                    source_advisor_briefing=briefing,
                    question=AUTO_RESEARCH_QUESTION,
                )
    except IntegrityError:
        existing = _existing_for_source(
            job=job,
            briefing=briefing,
        )
        if existing is not None:
            return existing, False

        active = ResearchRequest.objects.filter(
            startup_profile_id=startup_profile_id,
            status__in=ACTIVE_STATUSES,
        ).first()
        if active is not None:
            return active, False
        raise

    if research_request is None:
        return None, False

    return _dispatch_research(research_request)


def queue_research_after_advisor_job(
    *,
    job: StartupAdvisorBriefingJob,
    requested_by: Any,
) -> tuple[ResearchRequest | None, bool]:
    """Queue research from the durable advisor job, regardless of LLM outcome."""
    briefing = job.briefing if job.briefing_id else None
    return _queue_automatic_research(
        startup_profile_id=job.startup_profile_id,
        requested_by=requested_by,
        job=job,
        briefing=briefing,
    )


def queue_research_after_advisor(
    *,
    briefing: StartupAdvisorBriefing,
    requested_by: Any,
) -> tuple[ResearchRequest | None, bool]:
    """Link a successful briefing to its already-started research request."""
    try:
        job = briefing.generation_job
    except StartupAdvisorBriefingJob.DoesNotExist:
        job = None

    return _queue_automatic_research(
        startup_profile_id=briefing.startup_profile_id,
        requested_by=requested_by,
        job=job,
        briefing=briefing,
    )
