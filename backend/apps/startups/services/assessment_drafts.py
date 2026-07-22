from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.startups.assessment_schema import (
    startup_profile_to_assessment_data,
)
from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)


def get_or_create_startup_assessment_draft(
    *,
    owner: Any,
    startup_profile: StartupProfile | None,
    current_step: int,
    supplied_data: dict[str, Any],
) -> tuple[StartupAssessmentDraft, bool]:
    """Return the founder's active draft, creating it when necessary."""

    draft_data = (
        startup_profile_to_assessment_data(startup_profile) if startup_profile is not None else {}
    )
    draft_data.update(supplied_data)

    lookup = {
        "owner_id": owner.pk,
        "startup_profile_id": (startup_profile.pk if startup_profile is not None else None),
        "status": StartupAssessmentDraft.Status.DRAFT,
    }

    user_model = get_user_model()

    with transaction.atomic():
        user_model._default_manager.select_for_update().only(
            "pk",
        ).get(pk=owner.pk)

        existing = (
            StartupAssessmentDraft.objects.filter(**lookup).order_by("-updated_at", "-id").first()
        )
        if existing is not None:
            return existing, False

        try:
            with transaction.atomic():
                draft = StartupAssessmentDraft.objects.create(
                    owner=owner,
                    startup_profile=startup_profile,
                    current_step=current_step,
                    data=draft_data,
                )
        except IntegrityError:
            existing = (
                StartupAssessmentDraft.objects.filter(**lookup)
                .order_by("-updated_at", "-id")
                .first()
            )
            if existing is None:
                raise
            return existing, False

        return draft, True
