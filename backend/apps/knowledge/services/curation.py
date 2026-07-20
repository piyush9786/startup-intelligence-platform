from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.knowledge.models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateCuration,
    RequiredDocumentCandidate,
    SchemeCandidate,
)

ALLOWED_REVIEWER_ROLES = {
    "reviewer",
    "admin",
}

REVIEWABLE_MODELS = (
    BenefitCandidate,
    RequiredDocumentCandidate,
    ApplicationStepCandidate,
)


def _validate_reviewer(reviewer: Any) -> None:
    if reviewer is None:
        raise ValidationError("A reviewer is required.")

    if not getattr(
        reviewer,
        "is_authenticated",
        False,
    ):
        raise ValidationError("The reviewer must be authenticated.")

    if (
        not getattr(reviewer, "is_superuser", False)
        and getattr(reviewer, "role", None) not in ALLOWED_REVIEWER_ROLES
    ):
        raise ValidationError("Only reviewers or administrators may curate candidates.")


@transaction.atomic
def review_structured_item(
    *,
    item: (BenefitCandidate | RequiredDocumentCandidate | ApplicationStepCandidate),
    status: str,
    reviewer: Any | None,
    review_notes: str = "",
):
    if not isinstance(item, REVIEWABLE_MODELS):
        raise ValidationError("Unsupported structured candidate type.")

    valid_statuses = {value for value, _label in item.ReviewStatus.choices}

    if status not in valid_statuses:
        raise ValidationError("Unknown structured review status.")

    locked_item = item.__class__.objects.select_for_update().get(pk=item.pk)

    locked_item.review_status = status
    locked_item.review_notes = review_notes.strip()

    if status == item.ReviewStatus.DRAFT:
        locked_item.reviewed_by = None
        locked_item.reviewed_at = None
    else:
        _validate_reviewer(reviewer)
        locked_item.reviewed_by = reviewer
        locked_item.reviewed_at = timezone.now()

    locked_item.full_clean()
    locked_item.save()

    return locked_item


@transaction.atomic
def curate_candidate(
    *,
    candidate: SchemeCandidate,
    status: str,
    reviewer: Any | None,
    canonical_summary: str,
    official_url: str,
    canonical_objective: str = "",
    canonical_eligibility_text: str = "",
    application_url: str = "",
    review_notes: str = "",
    metadata: dict[str, Any] | None = None,
) -> CandidateCuration:
    valid_statuses = {value for value, _label in CandidateCuration.ReviewStatus.choices}

    if status not in valid_statuses:
        raise ValidationError("Unknown curation review status.")

    locked_candidate = SchemeCandidate.objects.select_for_update().get(pk=candidate.pk)

    try:
        curation = locked_candidate.curation
    except CandidateCuration.DoesNotExist:
        curation = CandidateCuration(
            candidate=locked_candidate,
        )

    curation.canonical_summary = canonical_summary.strip()
    curation.canonical_objective = canonical_objective.strip()
    curation.canonical_eligibility_text = canonical_eligibility_text.strip()
    curation.official_url = official_url.strip()
    curation.application_url = application_url.strip()
    curation.review_status = status
    curation.review_notes = review_notes.strip()

    if metadata is not None:
        curation.metadata = metadata

    if status == CandidateCuration.ReviewStatus.DRAFT:
        curation.reviewed_by = None
        curation.reviewed_at = None
    else:
        _validate_reviewer(reviewer)
        curation.reviewed_by = reviewer
        curation.reviewed_at = timezone.now()

    curation.full_clean()
    curation.save()

    return curation
