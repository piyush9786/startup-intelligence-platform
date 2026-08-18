"""Transactional state transitions for research jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.research.models import (
    ResearchRequest,
    StartupResearchReport,
)

if TYPE_CHECKING:
    from apps.research.orchestration.state import ResearchState


class ResearchJobStateError(RuntimeError):
    """Raised when a research job cannot make a valid transition."""


class StaleResearchTaskError(ResearchJobStateError):
    """Raised when an obsolete Celery delivery tries to run a job."""


@dataclass(frozen=True, slots=True)
class ResearchClaim:
    request: ResearchRequest
    existing_report: StartupResearchReport | None


def claim_research_request(
    research_request_id: str,
    *,
    task_id: str = "",
) -> ResearchClaim:
    """Lock and move a queued request to running.

    Returning an existing report makes task redelivery idempotent.
    """
    with transaction.atomic():
        request = (
            ResearchRequest.objects.select_for_update()
            .select_related("startup_profile", "requested_by")
            .get(pk=research_request_id)
        )
        existing_report = (
            StartupResearchReport.objects.filter(
                research_request=request,
            )
            .select_related("research_request")
            .first()
        )

        if request.status in {
            ResearchRequest.Status.SUCCEEDED,
            ResearchRequest.Status.PARTIAL,
        }:
            if existing_report is None:
                raise ResearchJobStateError(
                    "Research request finished without a report.",
                )
            return ResearchClaim(
                request=request,
                existing_report=existing_report,
            )

        if request.status == ResearchRequest.Status.FAILED:
            if existing_report is not None:
                return ResearchClaim(
                    request=request,
                    existing_report=existing_report,
                )
            raise ResearchJobStateError(
                "Failed research requests cannot be executed again "
                "without being re-queued.",
            )

        if (
            task_id
            and request.celery_task_id
            and request.celery_task_id != task_id
        ):
            raise StaleResearchTaskError(
                "This Celery delivery does not own the research job.",
            )

        now = timezone.now()
        update_fields = [
            "status",
            "started_at",
            "error_code",
            "error_message",
            "updated_at",
        ]

        request.status = ResearchRequest.Status.RUNNING
        request.started_at = request.started_at or now
        request.error_code = ""
        request.error_message = ""

        if task_id and not request.celery_task_id:
            request.celery_task_id = task_id
            update_fields.append("celery_task_id")

        request.save(update_fields=update_fields)
        return ResearchClaim(
            request=request,
            existing_report=None,
        )


def mark_research_failed(
    research_request_id: str,
    *,
    error_code: str,
    error_message: str,
    overwrite_failed: bool = False,
) -> bool:
    """Mark an active request failed without corrupting completed jobs."""
    with transaction.atomic():
        request = (
            ResearchRequest.objects.select_for_update()
            .filter(pk=research_request_id)
            .first()
        )
        if request is None:
            return False

        if request.status in {
            ResearchRequest.Status.SUCCEEDED,
            ResearchRequest.Status.PARTIAL,
        }:
            return False

        if (
            request.status == ResearchRequest.Status.FAILED
            and not overwrite_failed
        ):
            return False

        now = timezone.now()
        request.status = ResearchRequest.Status.FAILED
        request.completed_at = now
        request.error_code = str(error_code)[:64]
        request.error_message = str(error_message)[:4000]
        request.save(
            update_fields=[
                "status",
                "completed_at",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        return True


def persist_research_result(
    state: ResearchState,
) -> StartupResearchReport:
    """Persist one immutable report and complete the request atomically."""
    with transaction.atomic():
        request = (
            ResearchRequest.objects.select_for_update()
            .select_related("startup_profile")
            .get(pk=state.request_id)
        )
        existing_report = (
            StartupResearchReport.objects.filter(
                research_request=request,
            )
            .first()
        )
        if existing_report is not None:
            return existing_report

        if request.status == ResearchRequest.Status.FAILED:
            raise ResearchJobStateError(
                "A failed request cannot persist a successful report.",
            )

        now = timezone.now()
        report = StartupResearchReport.objects.create(
            startup_profile=request.startup_profile,
            research_request=request,
            local_data_cutoff=now,
            live_search_date=(
                now if state.live_evidence else None
            ),
            model_name=state.model_name or "unknown",
            algorithm_version="v1.3-adviser-decision-intelligence",
            report=state.report_data,
            source_snapshot=state.context_payload,
        )

        from apps.research.services.intelligence_memory import persist_report_intelligence

        persist_report_intelligence(report)

        request.status = (
            ResearchRequest.Status.PARTIAL
            if state.partial_results
            else ResearchRequest.Status.SUCCEEDED
        )
        request.completed_at = now
        request.error_code = (
            "partial_results" if state.partial_results else ""
        )
        request.error_message = (
            "; ".join(state.partial_messages)
            if state.partial_results
            else ""
        )
        request.save(
            update_fields=[
                "status",
                "completed_at",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        return report


def recover_stale_research_requests(
    *,
    now=None,
) -> int:
    """Fail abandoned queued/running jobs and release the unique lock."""
    current_time = now or timezone.now()
    queue_cutoff = current_time - timedelta(
        seconds=settings.RESEARCH_JOB_QUEUE_TIMEOUT_SECONDS,
    )
    running_cutoff = current_time - timedelta(
        seconds=settings.RESEARCH_JOB_RUNNING_TIMEOUT_SECONDS,
    )
    batch_size = settings.RESEARCH_STALE_RECOVERY_BATCH_SIZE

    stale_filter = (
        Q(
            status=ResearchRequest.Status.QUEUED,
            created_at__lt=queue_cutoff,
        )
        | Q(
            status=ResearchRequest.Status.RUNNING,
            started_at__lt=running_cutoff,
        )
        | Q(
            status=ResearchRequest.Status.RUNNING,
            started_at__isnull=True,
            updated_at__lt=running_cutoff,
        )
    )

    recovered = 0
    with transaction.atomic():
        requests = list(
            ResearchRequest.objects.select_for_update(
                skip_locked=True,
            )
            .filter(stale_filter)
            .order_by("created_at", "id")[:batch_size]
        )
        for request in requests:
            was_queued = (
                request.status == ResearchRequest.Status.QUEUED
            )
            request.status = ResearchRequest.Status.FAILED
            request.completed_at = current_time
            request.error_code = (
                "queue_timeout"
                if was_queued
                else "worker_interrupted"
            )
            request.error_message = (
                "The research request remained queued for too long."
                if was_queued
                else (
                    "The research worker stopped before completing "
                    "this request."
                )
            )
            request.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "error_code",
                    "error_message",
                    "updated_at",
                ]
            )
            recovered += 1

    return recovered
