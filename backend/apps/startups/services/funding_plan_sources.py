from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from apps.schemes.models import (
    GraphReviewStatus,
    PrerequisiteConcept,
    SchemePrerequisite,
    SchemeUnlock,
    SchemeVersion,
)
from apps.startups.models import StartupStartingPlan
from apps.startups.services.funding_plan import (
    FundingPlanDependency,
    FundingPlanInputError,
    FundingPlanStep,
)

SUPPORTED_STARTING_PLAN_VERSION = "startup-starting-plan-v1"

READINESS_URGENCY_RANKS = {
    "critical": 1,
    "blocker": 1,
    "required": 1,
    "high": 2,
    "recommended": 3,
    "medium": 3,
    "low": 4,
}


class FundingPlanSourceError(
    FundingPlanInputError,
):
    """Raised when persisted sources cannot form engine inputs."""


@dataclass(frozen=True, slots=True)
class FundingPlanSourceBundle:
    steps: tuple[FundingPlanStep, ...]
    dependencies: tuple[
        FundingPlanDependency,
        ...,
    ]
    source_snapshot: dict[str, Any]


def _canonical_uuid(
    value: Any,
    *,
    label: str,
) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise FundingPlanSourceError(f"{label} must contain a valid UUID.") from exc


def _positive_integer(
    value: Any,
    *,
    label: str,
) -> int:
    if isinstance(value, bool):
        raise FundingPlanSourceError(f"{label} must be a positive integer.")

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise FundingPlanSourceError(f"{label} must be a positive integer.") from exc

    if normalized < 1:
        raise FundingPlanSourceError(f"{label} must be a positive integer.")

    return normalized


def _source_document_snapshot(
    source_document,
) -> dict[str, Any]:
    return {
        "source_document_id": str(source_document.id),
        "source_url": (source_document.final_url or source_document.source_url),
        "title": source_document.title,
        "content_hash": (source_document.content_hash),
    }


def _reviewed_relationship_snapshot(
    relationship,
) -> dict[str, Any]:
    return {
        "relationship_id": str(relationship.id),
        "origin": relationship.origin,
        "review_status": (relationship.review_status),
        "evidence_text": (relationship.evidence_text),
        "evidence_page": (relationship.evidence_page),
        "reviewed_by_id": (
            str(relationship.reviewed_by_id) if relationship.reviewed_by_id else None
        ),
        "reviewed_at": (relationship.reviewed_at.isoformat() if relationship.reviewed_at else None),
        "source": _source_document_snapshot(relationship.source_document),
    }


def _processing_time_from_metadata(
    *,
    metadata: Any,
    source_document_id,
    label: str,
) -> tuple[
    int | None,
    int | None,
    dict[str, Any] | None,
]:
    if not isinstance(metadata, dict):
        raise FundingPlanSourceError(f"{label} metadata must be an object.")

    processing_time = metadata.get("processing_time_days")

    if processing_time is None:
        return None, None, None

    if not isinstance(processing_time, dict):
        raise FundingPlanSourceError(f"{label} processing time must be an object.")

    minimum = processing_time.get("minimum")
    maximum = processing_time.get("maximum")
    source_id = processing_time.get("source_document_id")

    if (
        isinstance(minimum, bool)
        or isinstance(maximum, bool)
        or not isinstance(minimum, int)
        or not isinstance(maximum, int)
    ):
        raise FundingPlanSourceError(f"{label} processing-time bounds must be integers.")

    if minimum < 0 or maximum < 0:
        raise FundingPlanSourceError(f"{label} processing-time bounds cannot be negative.")

    if minimum > maximum:
        raise FundingPlanSourceError(f"{label} processing-time range is inverted.")

    expected_source_id = str(source_document_id)

    if str(source_id) != expected_source_id:
        raise FundingPlanSourceError(
            f"{label} processing time must cite its verified source document."
        )

    return (
        minimum,
        maximum,
        {
            "minimum": minimum,
            "maximum": maximum,
            "source_document_id": (expected_source_id),
        },
    )


def _starting_plan_items(
    starting_plan: StartupStartingPlan,
) -> list[dict[str, Any]]:
    if starting_plan.plan_version != SUPPORTED_STARTING_PLAN_VERSION:
        raise FundingPlanSourceError(
            f"The funding-plan source must use {SUPPORTED_STARTING_PLAN_VERSION}."
        )

    if not isinstance(starting_plan.items, list):
        raise FundingPlanSourceError("The starting plan contains an invalid item snapshot.")

    normalized_items = []

    for item in starting_plan.items:
        if not isinstance(item, dict):
            raise FundingPlanSourceError("Every starting-plan item must be an object.")

        normalized_items.append(item)

    return normalized_items


def _readiness_step(
    *,
    item: dict[str, Any],
    starting_plan: StartupStartingPlan,
) -> FundingPlanStep:
    position = _positive_integer(
        item.get("position"),
        label="Readiness item position",
    )
    source = item.get("source")

    if not isinstance(source, dict):
        source = {}

    code = str(source.get("code") or f"action-{position}")
    action_plan_id = str(source.get("action_plan_id") or starting_plan.source_action_plan_id)
    priority = str(item.get("priority") or "recommended").lower()

    return FundingPlanStep(
        step_id=(f"readiness:{action_plan_id}:{code}:{position}"),
        title=str(item.get("title") or "Complete readiness action"),
        item_type="readiness_action",
        source_position=position,
        founder_urgency_rank=(
            READINESS_URGENCY_RANKS.get(
                priority,
                5,
            )
        ),
        funding_relevance_rank=100,
        parallelizable=True,
        metadata={
            "starting_plan_item": dict(item),
            "priority": priority,
            "source": dict(source),
            "destination": dict(
                item.get("destination")
                if isinstance(
                    item.get("destination"),
                    dict,
                )
                else {}
            ),
        },
    )


def _scheme_item_data(
    item: dict[str, Any],
) -> dict[str, Any]:
    position = _positive_integer(
        item.get("position"),
        label="Scheme item position",
    )
    source = item.get("source")

    if not isinstance(source, dict):
        raise FundingPlanSourceError("Every scheme opportunity requires a source snapshot.")

    scheme_version_id = _canonical_uuid(
        source.get("scheme_version_id"),
        label="Scheme version ID",
    )
    rank = _positive_integer(
        source.get("rank") or position,
        label="Recommendation rank",
    )

    return {
        "item": item,
        "source": source,
        "position": position,
        "rank": rank,
        "scheme_version_id": (scheme_version_id),
    }


def _verified_scheme_versions(
    scheme_item_data: list[dict[str, Any]],
) -> dict[str, SchemeVersion]:
    requested_ids = {row["scheme_version_id"] for row in scheme_item_data}

    versions = (
        SchemeVersion.objects.filter(
            id__in=requested_ids,
            verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
        )
        .select_related(
            "scheme__authority",
            "source_document",
        )
        .order_by("id")
    )

    version_by_id = {str(version.id): version for version in versions}
    missing_ids = sorted(requested_ids - set(version_by_id))

    if missing_ids:
        raise FundingPlanSourceError(
            "Starting-plan scheme opportunities "
            "must reference verified scheme versions: " + ", ".join(missing_ids)
        )

    return version_by_id


def _unlock_closure(
    *,
    recommended_version_ids: set[str],
    version_by_id: dict[
        str,
        SchemeVersion,
    ],
) -> tuple[
    dict[str, SchemeVersion],
    list[SchemeUnlock],
]:
    unlocks = list(
        SchemeUnlock.objects.filter(
            review_status=(GraphReviewStatus.VERIFIED),
        )
        .select_related(
            "predecessor_version__scheme__authority",
            "predecessor_version__source_document",
            "unlocked_version__scheme__authority",
            "unlocked_version__source_document",
            "source_document",
        )
        .order_by(
            "unlocked_version_id",
            "predecessor_version_id",
            "id",
        )
    )

    incoming: dict[
        str,
        list[SchemeUnlock],
    ] = defaultdict(list)

    for relationship in unlocks:
        incoming[str(relationship.unlocked_version_id)].append(relationship)

    included_ids = set(recommended_version_ids)
    frontier = list(sorted(recommended_version_ids))
    included_unlocks: list[SchemeUnlock] = []

    while frontier:
        unlocked_id = frontier.pop(0)

        for relationship in incoming.get(
            unlocked_id,
            [],
        ):
            predecessor = relationship.predecessor_version
            unlocked = relationship.unlocked_version

            for version in (
                predecessor,
                unlocked,
            ):
                if version.verification_status != SchemeVersion.VerificationStatus.VERIFIED:
                    raise FundingPlanSourceError(
                        "Verified unlock relationships must reference verified scheme versions."
                    )

                version_by_id[str(version.id)] = version

            if relationship not in included_unlocks:
                included_unlocks.append(relationship)

            predecessor_id = str(relationship.predecessor_version_id)

            if predecessor_id not in included_ids:
                included_ids.add(predecessor_id)
                frontier.append(predecessor_id)

    included_unlocks.sort(
        key=lambda relationship: (
            str(relationship.unlocked_version_id),
            str(relationship.predecessor_version_id),
            str(relationship.id),
        )
    )

    return version_by_id, included_unlocks


def _propagated_scheme_priorities(
    *,
    version_ids: set[str],
    recommended_rows_by_version: dict[
        str,
        dict[str, Any],
    ],
    unlocks: list[SchemeUnlock],
) -> tuple[
    dict[str, int],
    dict[str, int],
]:
    relevance_by_version = {
        version_id: (
            recommended_rows_by_version[version_id]["rank"]
            if version_id in recommended_rows_by_version
            else 100
        )
        for version_id in version_ids
    }
    position_by_version = {
        version_id: (
            recommended_rows_by_version[version_id]["position"]
            if version_id in recommended_rows_by_version
            else 1_000_000
        )
        for version_id in version_ids
    }

    for _iteration in range(max(len(version_ids), 1)):
        changed = False

        for relationship in unlocks:
            predecessor_id = str(relationship.predecessor_version_id)
            unlocked_id = str(relationship.unlocked_version_id)

            inherited_relevance = relevance_by_version[unlocked_id]
            inherited_position = position_by_version[unlocked_id]

            if inherited_relevance < relevance_by_version[predecessor_id]:
                relevance_by_version[predecessor_id] = inherited_relevance
                changed = True

            if inherited_position < position_by_version[predecessor_id]:
                position_by_version[predecessor_id] = inherited_position
                changed = True

        if not changed:
            break

    next_position = (
        max(
            (row["position"] for row in recommended_rows_by_version.values()),
            default=0,
        )
        + 1
    )

    for version_id in sorted(version_ids):
        if position_by_version[version_id] == 1_000_000:
            position_by_version[version_id] = next_position
            next_position += 1

    return (
        relevance_by_version,
        position_by_version,
    )


def _scheme_step(
    *,
    version: SchemeVersion,
    recommended_row: dict[
        str,
        Any,
    ]
    | None,
    relevance_rank: int,
    source_position: int,
) -> FundingPlanStep:
    is_recommended = recommended_row is not None

    if is_recommended:
        item = recommended_row["item"]
        title = str(item.get("title") or (f"Review {version.scheme.canonical_name}"))
        step_id = f"scheme:{version.id}"
        item_type = "scheme_opportunity"
        original_item = dict(item)
    else:
        title = f"Review dependency: {version.scheme.canonical_name}"
        step_id = f"scheme-dependency:{version.id}"
        item_type = "scheme_dependency_review"
        original_item = None

    return FundingPlanStep(
        step_id=step_id,
        title=title,
        item_type=item_type,
        source_position=source_position,
        founder_urgency_rank=100,
        funding_relevance_rank=(relevance_rank),
        application_status=(version.application_status),
        opening_date=version.opening_date,
        deadline=version.deadline,
        parallelizable=True,
        metadata={
            "scheme_id": str(version.scheme_id),
            "scheme_version_id": str(version.id),
            "scheme_name": (version.scheme.canonical_name),
            "authority_name": (version.scheme.authority.name),
            "recommended": is_recommended,
            "requires_eligibility_review": (not is_recommended),
            "original_starting_plan_item": (original_item),
            "source": (_source_document_snapshot(version.source_document)),
            "verified_by_id": (str(version.verified_by_id) if version.verified_by_id else None),
            "verified_at": (version.verified_at.isoformat() if version.verified_at else None),
        },
    )


def _prerequisite_step(
    *,
    prerequisite: PrerequisiteConcept,
    relationships: list[SchemePrerequisite],
    scheme_step_by_version: dict[
        str,
        FundingPlanStep,
    ],
) -> FundingPlanStep:
    (
        duration_min_days,
        duration_max_days,
        processing_time_snapshot,
    ) = _processing_time_from_metadata(
        metadata=prerequisite.metadata,
        source_document_id=(prerequisite.source_document_id),
        label=(f"Prerequisite {prerequisite.key!r}"),
    )

    successor_steps = [
        scheme_step_by_version[str(relationship.scheme_version_id)]
        for relationship in relationships
    ]

    return FundingPlanStep(
        step_id=(f"prerequisite:{prerequisite.id}"),
        title=f"Complete {prerequisite.name}",
        item_type="prerequisite",
        source_position=min(step.source_position for step in successor_steps),
        founder_urgency_rank=min(step.founder_urgency_rank for step in successor_steps),
        funding_relevance_rank=min(step.funding_relevance_rank for step in successor_steps),
        duration_min_days=duration_min_days,
        duration_max_days=duration_max_days,
        parallelizable=True,
        metadata={
            "prerequisite_id": str(prerequisite.id),
            "key": prerequisite.key,
            "name": prerequisite.name,
            "description": (prerequisite.description),
            "category": prerequisite.category,
            "evidence_text": (prerequisite.evidence_text),
            "evidence_page": (prerequisite.evidence_page),
            "processing_time": (processing_time_snapshot),
            "source": (_source_document_snapshot(prerequisite.source_document)),
            "verified_by_id": (
                str(prerequisite.verified_by_id) if prerequisite.verified_by_id else None
            ),
            "verified_at": (
                prerequisite.verified_at.isoformat() if prerequisite.verified_at else None
            ),
        },
    )


def build_funding_plan_source_bundle(
    *,
    starting_plan: StartupStartingPlan,
) -> FundingPlanSourceBundle:
    items = _starting_plan_items(starting_plan)
    readiness_items = [item for item in items if item.get("item_type") == "readiness_action"]
    scheme_items = [item for item in items if item.get("item_type") == "scheme_opportunity"]

    unsupported_types = sorted(
        {
            str(item.get("item_type"))
            for item in items
            if item.get("item_type")
            not in {
                "readiness_action",
                "scheme_opportunity",
            }
        }
    )

    if unsupported_types:
        raise FundingPlanSourceError(
            "The starting plan contains unsupported item types: " + ", ".join(unsupported_types)
        )

    scheme_rows = [_scheme_item_data(item) for item in scheme_items]
    recommended_rows_by_version: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in scheme_rows:
        version_id = row["scheme_version_id"]

        if version_id in recommended_rows_by_version:
            raise FundingPlanSourceError(
                "The starting plan contains duplicate scheme-version opportunities."
            )

        recommended_rows_by_version[version_id] = row

    version_by_id = _verified_scheme_versions(scheme_rows)
    recommended_version_ids = set(recommended_rows_by_version)

    (
        version_by_id,
        unlocks,
    ) = _unlock_closure(
        recommended_version_ids=(recommended_version_ids),
        version_by_id=version_by_id,
    )

    included_version_ids = set(version_by_id)
    (
        relevance_by_version,
        position_by_version,
    ) = _propagated_scheme_priorities(
        version_ids=included_version_ids,
        recommended_rows_by_version=(recommended_rows_by_version),
        unlocks=unlocks,
    )

    steps: list[FundingPlanStep] = [
        _readiness_step(
            item=item,
            starting_plan=starting_plan,
        )
        for item in readiness_items
    ]
    scheme_step_by_version: dict[
        str,
        FundingPlanStep,
    ] = {}

    for version_id in sorted(included_version_ids):
        scheme_step = _scheme_step(
            version=version_by_id[version_id],
            recommended_row=(recommended_rows_by_version.get(version_id)),
            relevance_rank=(relevance_by_version[version_id]),
            source_position=(position_by_version[version_id]),
        )
        scheme_step_by_version[version_id] = scheme_step
        steps.append(scheme_step)

    prerequisite_relationships = list(
        SchemePrerequisite.objects.filter(
            review_status=(GraphReviewStatus.VERIFIED),
            scheme_version_id__in=(included_version_ids),
        )
        .select_related(
            "scheme_version",
            "prerequisite__source_document",
            "source_document",
        )
        .order_by(
            "prerequisite_id",
            "scheme_version_id",
            "id",
        )
    )

    relationships_by_prerequisite: dict[
        str,
        list[SchemePrerequisite],
    ] = defaultdict(list)

    for relationship in prerequisite_relationships:
        prerequisite = relationship.prerequisite

        if prerequisite.lifecycle_status != PrerequisiteConcept.LifecycleStatus.VERIFIED:
            raise FundingPlanSourceError(
                "Verified prerequisite relationships must reference verified concepts."
            )

        relationships_by_prerequisite[str(relationship.prerequisite_id)].append(relationship)

    prerequisite_step_by_id: dict[
        str,
        FundingPlanStep,
    ] = {}

    for prerequisite_id in sorted(relationships_by_prerequisite):
        relationships = relationships_by_prerequisite[prerequisite_id]
        prerequisite = relationships[0].prerequisite
        prerequisite_step = _prerequisite_step(
            prerequisite=prerequisite,
            relationships=relationships,
            scheme_step_by_version=(scheme_step_by_version),
        )
        prerequisite_step_by_id[prerequisite_id] = prerequisite_step
        steps.append(prerequisite_step)

    dependencies: list[FundingPlanDependency] = []

    for relationship in prerequisite_relationships:
        prerequisite_id = str(relationship.prerequisite_id)
        successor_version_id = str(relationship.scheme_version_id)

        dependencies.append(
            FundingPlanDependency(
                relationship_id=(f"scheme-prerequisite:{relationship.id}"),
                predecessor_step_id=(prerequisite_step_by_id[prerequisite_id].step_id),
                successor_step_id=(scheme_step_by_version[successor_version_id].step_id),
                dependency_type=(relationship.requirement_type),
                metadata=(_reviewed_relationship_snapshot(relationship)),
            )
        )

    for relationship in unlocks:
        predecessor_version_id = str(relationship.predecessor_version_id)
        unlocked_version_id = str(relationship.unlocked_version_id)

        dependencies.append(
            FundingPlanDependency(
                relationship_id=(f"scheme-unlock:{relationship.id}"),
                predecessor_step_id=(scheme_step_by_version[predecessor_version_id].step_id),
                successor_step_id=(scheme_step_by_version[unlocked_version_id].step_id),
                dependency_type="hard",
                metadata=(_reviewed_relationship_snapshot(relationship)),
            )
        )

    steps.sort(
        key=lambda step: (
            step.source_position,
            step.step_id,
        )
    )
    dependencies.sort(
        key=lambda relationship: (
            relationship.successor_step_id,
            relationship.dependency_type,
            relationship.predecessor_step_id,
            relationship.relationship_id,
        )
    )

    synthetic_version_ids = sorted(included_version_ids - recommended_version_ids)

    return FundingPlanSourceBundle(
        steps=tuple(steps),
        dependencies=tuple(dependencies),
        source_snapshot={
            "starting_plan_id": str(starting_plan.id),
            "starting_plan_version": (starting_plan.plan_version),
            "graph_review_status": (GraphReviewStatus.VERIFIED),
            "recommended_scheme_version_ids": (sorted(recommended_version_ids)),
            "included_scheme_version_ids": (sorted(included_version_ids)),
            "synthetic_dependency_scheme_version_ids": (synthetic_version_ids),
            "prerequisite_concept_ids": (sorted(prerequisite_step_by_id)),
            "scheme_prerequisite_relationship_ids": [
                str(relationship.id) for relationship in prerequisite_relationships
            ],
            "scheme_unlock_relationship_ids": [str(relationship.id) for relationship in unlocks],
            "processing_time_policy": ("verified-prerequisite-metadata-only"),
        },
    )
