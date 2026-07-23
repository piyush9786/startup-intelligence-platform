from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.startups.models import (
    OnboardingProgress,
    StartupProfile,
)


class OnboardingProgressCompletedError(Exception):
    pass


def _initial_variant(owner):
    has_profile = StartupProfile.objects.filter(
        owner=owner,
    ).exists()

    if has_profile:
        return OnboardingProgress.Variant.RETURNING_FOUNDER

    return OnboardingProgress.Variant.EMPTY_PROFILE


@transaction.atomic
def get_or_create_onboarding_progress(*, owner):
    user_model = get_user_model()
    locked_owner = user_model.objects.select_for_update().get(
        pk=owner.pk,
    )

    progress, created = OnboardingProgress.objects.get_or_create(
        owner=locked_owner,
        defaults={
            "tour_version": (OnboardingProgress.TOUR_VERSION),
            "variant": _initial_variant(
                locked_owner,
            ),
            "status": (OnboardingProgress.Status.ACTIVE),
            "current_step": 1,
        },
    )

    return progress, created


@transaction.atomic
def apply_onboarding_action(
    *,
    owner,
    action,
    current_step=None,
):
    progress, _ = get_or_create_onboarding_progress(
        owner=owner,
    )

    if progress.status == OnboardingProgress.Status.COMPLETED:
        raise OnboardingProgressCompletedError("Completed onboarding cannot be reopened.")

    now = timezone.now()

    if action == "set_step":
        progress.status = OnboardingProgress.Status.ACTIVE
        progress.current_step = current_step
        progress.dismissed_at = None
        progress.completed_at = None

    elif action == "dismiss":
        progress.status = OnboardingProgress.Status.DISMISSED
        progress.dismissed_at = now
        progress.completed_at = None

    elif action == "resume":
        progress.status = OnboardingProgress.Status.ACTIVE
        progress.dismissed_at = None
        progress.completed_at = None

    elif action == "complete":
        progress.status = OnboardingProgress.Status.COMPLETED
        progress.current_step = OnboardingProgress.TOTAL_STEPS
        progress.dismissed_at = None
        progress.completed_at = now

    else:
        raise ValueError(f"Unsupported onboarding action: {action!r}")

    progress.save()
    return progress
