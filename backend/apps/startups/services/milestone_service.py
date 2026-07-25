"""
Milestone execution business logic and dependency validation.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.startups.models import StartupMilestone


class MilestoneError(RuntimeError):
    pass


class MilestoneDependencyError(MilestoneError):
    pass


class MilestoneCycleError(MilestoneError):
    pass


def check_prerequisites_completed(
    milestone: StartupMilestone,
) -> tuple[bool, list[str]]:
    """
    Return whether all prerequisite milestones are completed and the titles of
    any incomplete prerequisites.
    """
    uncompleted = list(
        milestone.dependencies.exclude(
            status=StartupMilestone.Status.COMPLETED,
        ).values_list(
            "title",
            flat=True,
        )
    )
    return not uncompleted, uncompleted


def detect_dependency_cycle(
    milestone_id: str | None,
    target_dependency_ids: list[str],
    *,
    owner_id,
    startup_profile_id,
) -> bool:
    """
    Check whether the proposed dependencies introduce a cycle.

    Traversal is strictly scoped to one founder and one startup profile.
    """
    if not milestone_id:
        return False

    scoped_milestones = StartupMilestone.objects.filter(
        owner_id=owner_id,
        startup_profile_id=startup_profile_id,
    ).prefetch_related("dependencies")

    dependency_map = {
        str(milestone.id): [
            str(dependency.id)
            for dependency in milestone.dependencies.all()
            if dependency.owner_id == owner_id
            and dependency.startup_profile_id == startup_profile_id
        ]
        for milestone in scoped_milestones
    }

    root_id = str(milestone_id)

    def reaches_root(current_id: str, visited: set[str]) -> bool:
        if current_id == root_id:
            return True

        if current_id in visited:
            return False

        visited.add(current_id)

        for dependency_id in dependency_map.get(current_id, []):
            if reaches_root(dependency_id, visited):
                return True

        return False

    for dependency_id in target_dependency_ids:
        normalized_id = str(dependency_id)

        if normalized_id == root_id:
            return True

        if reaches_root(normalized_id, set()):
            return True

    return False


@transaction.atomic
def complete_milestone(
    *,
    milestone: StartupMilestone,
    evidence: dict[str, Any] | None = None,
) -> StartupMilestone:
    """
    Complete a milestone only when every prerequisite is completed.

    There is intentionally no founder-controlled force override.
    """
    locked = StartupMilestone.objects.select_for_update().get(
        pk=milestone.pk,
        owner_id=milestone.owner_id,
        startup_profile_id=milestone.startup_profile_id,
    )

    all_done, uncompleted = check_prerequisites_completed(locked)
    if not all_done:
        titles = ", ".join(f"'{title}'" for title in uncompleted)
        raise MilestoneDependencyError(
            f"Cannot complete milestone. Prerequisite milestones are incomplete: {titles}."
        )

    now = timezone.now()

    locked.status = StartupMilestone.Status.COMPLETED
    locked.completed_at = now

    if evidence:
        locked.completion_evidence = evidence

    updates = list(locked.updates_log or [])
    updates.append(
        {
            "timestamp": now.isoformat(),
            "action": "completed",
            "note": "Milestone marked as completed.",
            "evidence": evidence or {},
        }
    )
    locked.updates_log = updates

    locked.save(
        update_fields=[
            "status",
            "completed_at",
            "completion_evidence",
            "updates_log",
            "updated_at",
        ]
    )
    return locked


@transaction.atomic
def append_milestone_log(
    *,
    milestone: StartupMilestone,
    note: str,
    author: str = "founder",
) -> StartupMilestone:
    """
    Append a founder update while holding a database lock so concurrent updates
    cannot overwrite each other.
    """
    locked = StartupMilestone.objects.select_for_update().get(
        pk=milestone.pk,
        owner_id=milestone.owner_id,
        startup_profile_id=milestone.startup_profile_id,
    )

    updates = list(locked.updates_log or [])
    updates.append(
        {
            "timestamp": timezone.now().isoformat(),
            "author": author,
            "action": "update",
            "note": note,
        }
    )
    locked.updates_log = updates
    locked.save(update_fields=["updates_log", "updated_at"])
    return locked
