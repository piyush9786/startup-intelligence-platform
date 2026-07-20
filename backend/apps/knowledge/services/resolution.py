from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.knowledge.models import (
    CandidateResolution,
    SchemeCandidate,
)
from apps.schemes.models import Authority


PUBLISHABLE_CLASSIFICATIONS = {
    CandidateResolution.Classification.CANONICAL,
    CandidateResolution.Classification.SUPPORTING,
}

PRIMARY_REQUIRED_CLASSIFICATIONS = {
    CandidateResolution.Classification.SUPPORTING,
    CandidateResolution.Classification.DUPLICATE,
}

ALLOWED_REVIEWER_ROLES = {
    "reviewer",
    "admin",
}


def _validate_reviewer(reviewer: Any) -> None:
    if reviewer is None:
        raise ValidationError(
            "A reviewer is required."
        )

    if not getattr(reviewer, "is_authenticated", False):
        raise ValidationError(
            "The reviewer must be authenticated."
        )

    if (
        not getattr(reviewer, "is_superuser", False)
        and getattr(reviewer, "role", None)
        not in ALLOWED_REVIEWER_ROLES
    ):
        raise ValidationError(
            "Only reviewers or administrators may "
            "resolve candidates."
        )


def _validate_primary_candidate(
    *,
    candidate: SchemeCandidate,
    primary_candidate: SchemeCandidate | None,
) -> SchemeCandidate:
    if primary_candidate is None:
        raise ValidationError(
            "A primary candidate is required."
        )

    if primary_candidate.pk == candidate.pk:
        raise ValidationError(
            "A candidate cannot reference itself "
            "as primary."
        )

    locked_primary = (
        SchemeCandidate.objects
        .select_for_update()
        .get(pk=primary_candidate.pk)
    )

    try:
        primary_resolution = (
            locked_primary.resolution
        )
    except CandidateResolution.DoesNotExist as exc:
        raise ValidationError(
            "The primary candidate must already have "
            "a canonical resolution."
        ) from exc

    if (
        primary_resolution.classification
        != CandidateResolution.Classification.CANONICAL
    ):
        raise ValidationError(
            "The primary candidate must have "
            "a canonical resolution."
        )

    return locked_primary


@transaction.atomic
def resolve_candidate(
    *,
    candidate: SchemeCandidate,
    classification: str,
    reviewer: Any | None,
    canonical_title: str = "",
    resolved_authority: Authority | None = None,
    primary_candidate: SchemeCandidate | None = None,
    review_notes: str = "",
    metadata: dict[str, Any] | None = None,
) -> CandidateResolution:
    valid_classifications = {
        value
        for value, _label
        in CandidateResolution.Classification.choices
    }

    if classification not in valid_classifications:
        raise ValidationError(
            "Unknown candidate classification."
        )

    locked_candidate = (
        SchemeCandidate.objects
        .select_for_update()
        .get(pk=candidate.pk)
    )

    if (
        locked_candidate.review_status
        == SchemeCandidate.ReviewStatus.PUBLISHED
    ):
        raise ValidationError(
            "Published candidates cannot be re-resolved."
        )

    unresolved = (
        classification
        == CandidateResolution.Classification.UNRESOLVED
    )

    if not unresolved:
        _validate_reviewer(reviewer)

    canonical_title = canonical_title.strip()

    if classification in PUBLISHABLE_CLASSIFICATIONS:
        if not canonical_title:
            raise ValidationError(
                "Canonical and supporting candidates "
                "require a canonical title."
            )

        if resolved_authority is None:
            raise ValidationError(
                "Canonical and supporting candidates "
                "require a resolved authority."
            )

    locked_primary = None

    if classification in PRIMARY_REQUIRED_CLASSIFICATIONS:
        locked_primary = _validate_primary_candidate(
            candidate=locked_candidate,
            primary_candidate=primary_candidate,
        )

    try:
        resolution = locked_candidate.resolution
    except CandidateResolution.DoesNotExist:
        resolution = CandidateResolution(
            candidate=locked_candidate,
        )

    resolution.canonical_title = canonical_title
    resolution.resolved_authority = resolved_authority
    resolution.classification = classification
    resolution.primary_candidate = locked_primary
    resolution.review_notes = review_notes.strip()
    resolution.metadata = (
        metadata
        if metadata is not None
        else resolution.metadata
    )

    if unresolved:
        resolution.resolved_by = None
        resolution.resolved_at = None
    else:
        resolution.resolved_by = reviewer
        resolution.resolved_at = timezone.now()

    resolution.full_clean()
    resolution.save()

    if classification in PUBLISHABLE_CLASSIFICATIONS:
        next_status = (
            SchemeCandidate.ReviewStatus.APPROVED
        )
    elif classification in {
        CandidateResolution.Classification.DUPLICATE,
        CandidateResolution.Classification.REJECTED,
    }:
        next_status = (
            SchemeCandidate.ReviewStatus.REJECTED
        )
    else:
        next_status = (
            SchemeCandidate.ReviewStatus.NEEDS_REVIEW
        )

    if locked_candidate.review_status != next_status:
        locked_candidate.review_status = next_status
        locked_candidate.save(
            update_fields=[
                "review_status",
                "updated_at",
            ]
        )

    return resolution
