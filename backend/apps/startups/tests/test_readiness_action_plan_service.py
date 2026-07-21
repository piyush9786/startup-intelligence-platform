from datetime import date

import pytest

from apps.startups.models import StartupReadinessActionPlan
from apps.startups.services import (
    ACTION_PLAN_VERSION,
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)
from apps.startups.tests.test_readiness_assessment_api import (
    make_profile,
    make_user,
)

pytestmark = pytest.mark.django_db


def make_assessment(*, owner, name: str, actionable: bool = True):
    profile = make_profile(owner=owner, name=name)
    if actionable:
        profile.description = ""
        profile.save(update_fields=["description", "updated_at"])
    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    return profile, assessment


def test_service_persists_plan_and_source_snapshot():
    owner = make_user(username="action-plan-service-owner")
    profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan Service Startup",
    )

    plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    assert plan.startup_profile == profile
    assert plan.source_assessment == assessment
    assert plan.requested_by == owner
    assert plan.readiness_status == assessment.status
    assert plan.has_actions is True
    assert plan.blocker_count == 0
    assert plan.recommendation_count >= 1
    assert plan.total_action_count == len(plan.items)
    assert plan.next_action == plan.items[0]["action"]
    assert plan.source_engine_version == assessment.engine_version
    assert plan.planner_version == ACTION_PLAN_VERSION
    snapshot = plan.source_assessment_snapshot
    assert snapshot["id"] == str(assessment.id)
    assert snapshot["startup_profile_id"] == str(profile.id)
    assert snapshot["profile_snapshot"] == assessment.profile_snapshot
    assert snapshot["findings"] == assessment.findings


def test_service_retains_historical_plans():
    owner = make_user(username="action-plan-history-owner")
    _profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan History Startup",
    )

    first = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    second = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    assert first.id != second.id
    assert StartupReadinessActionPlan.objects.count() == 2
    assert list(assessment.action_plans.values_list("id", flat=True)) == [second.id, first.id]


def test_service_does_not_recalculate_readiness(monkeypatch):
    owner = make_user(username="action-plan-no-recalc-owner")
    profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan No Recalc Startup",
    )
    original_findings = assessment.findings

    profile.description = "Changed after the assessment."
    profile.dpiit_recognized = None
    profile.save(
        update_fields=[
            "description",
            "dpiit_recognized",
            "updated_at",
        ]
    )

    def fail_recalculation(*args, **kwargs):
        raise AssertionError("Readiness must not be recalculated.")

    monkeypatch.setattr(
        "apps.startups.services.assessment.evaluate_startup_readiness",
        fail_recalculation,
    )
    monkeypatch.setattr(
        "apps.startups.services.readiness.evaluate_startup_readiness",
        fail_recalculation,
    )

    plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    assert plan.source_assessment_snapshot["findings"] == (original_findings)
    assert plan.source_assessment_snapshot["profile_snapshot"]["dpiit_recognized"] is True


def test_ready_assessment_persists_empty_plan():
    owner = make_user(username="action-plan-ready-owner")
    _profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan Ready Startup",
        actionable=False,
    )

    plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    assert plan.readiness_status == "ready"
    assert plan.has_actions is False
    assert plan.blocker_count == 0
    assert plan.recommendation_count == 0
    assert plan.total_action_count == 0
    assert plan.next_action is None
    assert plan.items == []
