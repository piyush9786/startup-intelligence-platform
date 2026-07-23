from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.recommendations.services import generate_recommendations

from ..assessment_schema import (
    DIRECT_PROFILE_FIELDS,
    PROFILE_DATA_FIELDS,
)
from ..models import (
    StartupAssessmentDraft,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
    StartupStartingPlan,
)
from ..serializers import StartupAssessmentSubmissionSerializer
from .action_plan_persistence import create_startup_readiness_action_plan
from .assessment import (
    create_startup_readiness_assessment,
    snapshot_startup_profile,
)
from .starting_plan import create_startup_starting_plan


class AssessmentDraftAlreadySubmittedError(RuntimeError):
    pass


@dataclass(frozen=True)
class StartupAssessmentSubmission:
    draft: StartupAssessmentDraft
    startup_profile: StartupProfile
    readiness_assessment: StartupReadinessAssessment
    action_plan: StartupReadinessActionPlan
    recommendation_generation: Any
    starting_plan: StartupStartingPlan


@transaction.atomic
def submit_startup_assessment_draft(
    *,
    draft: StartupAssessmentDraft,
    requested_by: Any,
) -> StartupAssessmentSubmission:
    user_model = get_user_model()
    user_model._default_manager.select_for_update().only(
        "pk",
    ).get(pk=draft.owner_id)

    locked_draft = (
        StartupAssessmentDraft.objects.select_for_update(
            of=("self",),
        )
        .select_related("owner", "startup_profile")
        .get(pk=draft.pk)
    )
    if locked_draft.status != StartupAssessmentDraft.Status.DRAFT:
        raise AssessmentDraftAlreadySubmittedError(
            "This startup assessment draft has already been submitted."
        )

    submission_serializer = StartupAssessmentSubmissionSerializer(
        data=locked_draft.data,
    )
    submission_serializer.is_valid(raise_exception=True)
    validated_data = dict(submission_serializer.validated_data)

    startup_profile = locked_draft.startup_profile
    if startup_profile is None:
        startup_profile = StartupProfile(owner=locked_draft.owner)
    elif startup_profile.owner_id != locked_draft.owner_id:
        raise serializers.ValidationError(
            {"startup_profile": "The linked startup profile owner does not match the draft owner."}
        )

    for field_name in DIRECT_PROFILE_FIELDS:
        if field_name in validated_data:
            setattr(
                startup_profile,
                field_name,
                validated_data[field_name],
            )

    profile_data = dict(startup_profile.profile_data or {})
    for field_name in PROFILE_DATA_FIELDS:
        if field_name in validated_data:
            profile_data[field_name] = validated_data[field_name]
    startup_profile.profile_data = profile_data
    startup_profile.save()

    readiness_assessment = create_startup_readiness_assessment(
        startup_profile=startup_profile,
        requested_by=requested_by,
        assessment_date=timezone.localdate(),
    )
    action_plan = create_startup_readiness_action_plan(
        source_assessment=readiness_assessment,
        requested_by=requested_by,
    )
    recommendation_generation = generate_recommendations(
        startup_profile=startup_profile,
        requested_by=requested_by,
        assessment_date=timezone.localdate(),
    )
    starting_plan = create_startup_starting_plan(
        source_assessment=readiness_assessment,
        source_action_plan=action_plan,
        recommendation_generation_run=(
            recommendation_generation.generation_run
        ),
        requested_by=requested_by,
    ).plan

    locked_draft.startup_profile = startup_profile
    locked_draft.status = StartupAssessmentDraft.Status.SUBMITTED
    locked_draft.current_step = 8
    locked_draft.submitted_at = timezone.now()
    locked_draft.submitted_profile_snapshot = snapshot_startup_profile(
        startup_profile,
    )
    locked_draft.save(
        update_fields=(
            "startup_profile",
            "status",
            "current_step",
            "submitted_at",
            "submitted_profile_snapshot",
            "updated_at",
        )
    )

    return StartupAssessmentSubmission(
        draft=locked_draft,
        startup_profile=startup_profile,
        readiness_assessment=readiness_assessment,
        action_plan=action_plan,
        recommendation_generation=recommendation_generation,
        starting_plan=starting_plan,
    )
