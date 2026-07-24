"""
Milestone execution business logic & dependency validation.
"""
from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.startups.models import StartupMilestone

logger = logging.getLogger(__name__)


class MilestoneError(RuntimeError):
    pass


class MilestoneDependencyError(MilestoneError):
    pass


class MilestoneCycleError(MilestoneError):
    pass


def check_prerequisites_completed(milestone: StartupMilestone) -> tuple[bool, list[str]]:
    """
    Check if all prerequisite milestones for the given milestone are completed.
    Returns (all_completed: bool, uncompleted_titles: list[str]).
    """
    uncompleted = []
    for dep in milestone.dependencies.all():
        if dep.status != StartupMilestone.Status.COMPLETED:
            uncompleted.append(dep.title)

    return (len(uncompleted) == 0, uncompleted)


def detect_dependency_cycle(
    milestone_id: str | None,
    target_dependency_ids: list[str],
) -> bool:
    """
    Check if adding target_dependency_ids to milestone_id creates a cycle.
    """
    if not milestone_id:
        return False

    visited = set()

    def dfs(current_id: str) -> bool:
        if current_id == str(milestone_id):
            return True
        if current_id in visited:
            return False
        visited.add(current_id)

        try:
            m = StartupMilestone.objects.get(id=current_id)
            for dep in m.dependencies.all():
                if dfs(str(dep.id)):
                    return True
        except StartupMilestone.DoesNotExist:
            pass

        return False

    for dep_id in target_dependency_ids:
        if str(dep_id) == str(milestone_id) or dfs(str(dep_id)):
            return True

    return False


def complete_milestone(
    *,
    milestone: StartupMilestone,
    evidence: dict[str, Any] | None = None,
    force: bool = False,
) -> StartupMilestone:
    """
    Mark a milestone as COMPLETED. Checks prerequisite dependencies unless force=True.
    """
    if not force:
        all_done, uncompleted = check_prerequisites_completed(milestone)
        if not all_done:
            titles = ", ".join(f"'{t}'" for t in uncompleted)
            raise MilestoneDependencyError(
                f"Cannot complete milestone. Prerequisite milestones are incomplete: {titles}."
            )

    milestone.status = StartupMilestone.Status.COMPLETED
    milestone.completed_at = timezone.now()
    if evidence:
        milestone.completion_evidence = evidence

    # Log update
    log_entry = {
        "timestamp": timezone.now().isoformat(),
        "action": "completed",
        "note": "Milestone marked as completed.",
        "evidence": evidence or {},
    }
    updates = list(milestone.updates_log or [])
    updates.append(log_entry)
    milestone.updates_log = updates

    milestone.save()
    return milestone


def append_milestone_log(
    *,
    milestone: StartupMilestone,
    note: str,
    author: str = "founder",
) -> StartupMilestone:
    """
    Append a chronological founder update log to a milestone.
    """
    log_entry = {
        "timestamp": timezone.now().isoformat(),
        "author": author,
        "action": "update",
        "note": note,
    }
    updates = list(milestone.updates_log or [])
    updates.append(log_entry)
    milestone.updates_log = updates
    milestone.save(update_fields=["updates_log", "updated_at"])
    return milestone
