from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.serializers.json import (
    DjangoJSONEncoder,
)
from django.db import transaction

from apps.startups.models import (
    StartupFundingPlan,
    StartupProfile,
    StartupStartingPlan,
)
from apps.startups.services.funding_plan import (
    FUNDING_PLAN_VERSION,
    FundingPlanDependency,
    FundingPlanStep,
    order_funding_plan,
)
from apps.startups.services.funding_plan_sources import (
    FundingPlanSourceBundle,
    FundingPlanSourceError,
    build_funding_plan_source_bundle,
)


@dataclass(frozen=True, slots=True)
class FundingPlanPersistenceResult:
    plan: StartupFundingPlan
    created: bool


def _json_safe(
    value: Any,
) -> Any:
    return json.loads(
        json.dumps(
            value,
            cls=DjangoJSONEncoder,
            ensure_ascii=False,
        )
    )


def _step_source_snapshot(
    step: FundingPlanStep,
) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "title": step.title,
        "item_type": step.item_type,
        "source_position": (step.source_position),
        "founder_urgency_rank": (step.founder_urgency_rank),
        "funding_relevance_rank": (step.funding_relevance_rank),
        "application_status": (step.application_status),
        "opening_date": (step.opening_date.isoformat() if step.opening_date else None),
        "deadline": (step.deadline.isoformat() if step.deadline else None),
        "duration_min_days": (step.duration_min_days),
        "duration_max_days": (step.duration_max_days),
        "parallelizable": (step.parallelizable),
        "metadata": dict(step.metadata),
    }


def _dependency_source_snapshot(
    dependency: FundingPlanDependency,
) -> dict[str, Any]:
    return {
        "relationship_id": (dependency.relationship_id),
        "predecessor_step_id": (dependency.predecessor_step_id),
        "successor_step_id": (dependency.successor_step_id),
        "dependency_type": (dependency.dependency_type),
        "metadata": dict(dependency.metadata),
    }


def _canonical_source_snapshot(
    *,
    bundle: FundingPlanSourceBundle,
    as_of_date: date,
) -> dict[str, Any]:
    steps = sorted(
        (_step_source_snapshot(step) for step in bundle.steps),
        key=lambda item: (
            item["step_id"],
            item["source_position"],
        ),
    )
    dependencies = sorted(
        (_dependency_source_snapshot(dependency) for dependency in bundle.dependencies),
        key=lambda item: (
            item["successor_step_id"],
            item["dependency_type"],
            item["predecessor_step_id"],
            item["relationship_id"],
        ),
    )

    return _json_safe(
        {
            "planner_version": (FUNDING_PLAN_VERSION),
            "as_of_date": (as_of_date.isoformat()),
            "source": dict(bundle.source_snapshot),
            "steps": steps,
            "dependencies": dependencies,
        }
    )


def _source_hash(
    source_snapshot: dict[str, Any],
) -> str:
    canonical_json = json.dumps(
        source_snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@transaction.atomic
def create_startup_funding_plan(
    *,
    source_starting_plan: (StartupStartingPlan),
    requested_by: Any,
    as_of_date: date,
) -> FundingPlanPersistenceResult:
    if source_starting_plan.pk is None:
        raise FundingPlanSourceError("The source starting plan must be persisted.")

    locked_starting_plan = (
        StartupStartingPlan.objects.select_for_update()
        .select_related(
            "startup_profile",
        )
        .get(pk=source_starting_plan.pk)
    )
    profile = StartupProfile.objects.select_for_update().get(
        pk=(locked_starting_plan.startup_profile_id)
    )

    bundle = build_funding_plan_source_bundle(
        starting_plan=(locked_starting_plan),
    )
    source_snapshot = _canonical_source_snapshot(
        bundle=bundle,
        as_of_date=as_of_date,
    )
    source_hash = _source_hash(source_snapshot)
    plan_snapshot = _json_safe(
        order_funding_plan(
            steps=list(bundle.steps),
            dependencies=list(bundle.dependencies),
            as_of_date=as_of_date,
        )
    )

    existing = (
        StartupFundingPlan.objects.select_for_update()
        .filter(
            source_starting_plan=(locked_starting_plan),
            as_of_date=as_of_date,
            source_hash=source_hash,
            plan_version=(FUNDING_PLAN_VERSION),
        )
        .first()
    )

    StartupFundingPlan.objects.filter(
        startup_profile=profile,
        is_current=True,
    ).exclude(
        pk=getattr(
            existing,
            "pk",
            None,
        ),
    ).update(
        is_current=False,
    )

    if existing is not None:
        if not existing.is_current:
            existing.is_current = True
            existing.save(
                update_fields=[
                    "is_current",
                    "updated_at",
                ]
            )

        return FundingPlanPersistenceResult(
            plan=existing,
            created=False,
        )

    plan = StartupFundingPlan.objects.create(
        requested_by=requested_by,
        startup_profile=profile,
        source_starting_plan=(locked_starting_plan),
        as_of_date=as_of_date,
        source_hash=source_hash,
        source_snapshot=source_snapshot,
        plan_snapshot=plan_snapshot,
        step_count=(plan_snapshot["total_step_count"]),
        dependency_count=len(plan_snapshot["dependencies"]),
        execution_wave_count=(plan_snapshot["execution_wave_count"]),
        next_step_ids=list(plan_snapshot["next_step_ids"]),
        plan_version=(FUNDING_PLAN_VERSION),
        is_current=True,
    )

    return FundingPlanPersistenceResult(
        plan=plan,
        created=True,
    )
