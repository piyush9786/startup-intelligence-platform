"""
Shared utility functions for the startups application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.startups.models import StartupProfile


def get_current_startup_profile(user: AbstractBaseUser) -> StartupProfile | None:
    """
    Retrieve the most recently created StartupProfile for a given user.
    """
    from apps.startups.models import StartupProfile

    return (
        StartupProfile.objects.filter(owner=user)
        .order_by("-created_at")
        .first()
    )
