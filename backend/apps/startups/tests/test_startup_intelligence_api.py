from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.startups.models import (
    StartupBuilderSection,
    StartupCapitalPlan,
    StartupMilestone,
    StartupProfile,
    StartupReadinessAssessment,
)

User = get_user_model()


def _make_profile(owner, name="IntelTest Startup"):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage="mvp",
        state="Karnataka",
    )


def _make_readiness(profile, score=72):
    from django.utils import timezone
    return StartupReadinessAssessment.objects.create(
        requested_by=profile.owner,
        startup_profile=profile,
        assessment_date=timezone.localdate(),
        status="ready_with_recommendations",
        score=score,
        critical_score=60,
        recommended_score=80,
        findings=[{"domain": "financial", "label": "OK"}],
        blocking_findings=[],
        summary="Test readiness summary",
        engine_version="rules-v5",
    )


def _make_capital_plan(profile):
    return StartupCapitalPlan.objects.create(
        owner=profile.owner,
        startup_profile=profile,
        available_capital=Decimal("1500000"),
        monthly_revenue=Decimal("100000"),
        fixed_costs=Decimal("150000"),
        variable_costs=Decimal("60000"),
        net_burn=Decimal("110000"),
        runway_months=Decimal("13.6"),
        runway_status=StartupCapitalPlan.RunwayStatus.CAUTION,
        scenarios={},
        allocations={},
        sensitivity={},
    )


def _make_milestones(profile, n_complete=3, n_inprog=2):
    milestones = []
    from django.utils import timezone
    for i in range(n_complete):
        m = StartupMilestone.objects.create(
            owner=profile.owner,
            startup_profile=profile,
            title=f"Completed M{i}",
            status=StartupMilestone.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        milestones.append(m)
    for i in range(n_inprog):
        m = StartupMilestone.objects.create(
            owner=profile.owner,
            startup_profile=profile,
            title=f"InProgress M{i}",
            status=StartupMilestone.Status.IN_PROGRESS,
        )
        milestones.append(m)
    return milestones


class StartupIntelligenceAPITests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="intel_founder",
            email="intel_founder@example.com",
            password="Password123!",
            role="founder",
        )
        self.profile = _make_profile(self.founder)

    def _url(self, profile=None):
        return reverse(
            "startup-intelligence",
            kwargs={"profile_id": str((profile or self.profile).pk)},
        )

    def test_empty_profile_returns_all_zeros(self):
        self.client.force_authenticate(user=self.founder)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["readiness"]["has_assessment"], False)
        self.assertIsNone(data["readiness"]["score"])
        self.assertEqual(data["capital"]["has_plan"], False)
        self.assertEqual(data["milestones"]["total"], 0)
        self.assertEqual(data["milestones"]["completion_pct"], 0)
        self.assertEqual(data["builder"]["sections_confirmed"], 0)
        self.assertEqual(data["schemes"]["matched"], 0)
        self.assertEqual(data["recent_activity"], [])
        # Weakest workspace should be 'startup' when no assessment
        self.assertEqual(data["weakest_workspace"], "startup")

    def test_populated_profile_returns_correct_metrics(self):
        self.client.force_authenticate(user=self.founder)
        _make_readiness(self.profile, score=72)
        _make_capital_plan(self.profile)
        _make_milestones(self.profile, n_complete=3, n_inprog=2)

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertTrue(data["readiness"]["has_assessment"])
        self.assertEqual(data["readiness"]["score"], 72)
        self.assertEqual(data["readiness"]["grade"], "B")

        self.assertTrue(data["capital"]["has_plan"])
        self.assertEqual(data["capital"]["runway_status"], "caution")
        self.assertAlmostEqual(float(data["capital"]["runway_months"]), 13.6, places=0)

        self.assertEqual(data["milestones"]["total"], 5)
        self.assertEqual(data["milestones"]["completed"], 3)
        self.assertEqual(data["milestones"]["in_progress"], 2)
        self.assertEqual(data["milestones"]["completion_pct"], 60)

    def test_readiness_grade_thresholds(self):
        self.client.force_authenticate(user=self.founder)
        for score, expected_grade in [(92, "A"), (72, "B"), (57, "C"), (42, "D"), (30, "F")]:
            self.profile.readiness_assessments.all().delete()
            _make_readiness(self.profile, score=score)
            response = self.client.get(self._url())
            self.assertEqual(
                response.data["readiness"]["grade"], expected_grade, msg=f"score={score}"
            )

    def test_builder_completion_pct_reflects_confirmed_sections(self):
        self.client.force_authenticate(user=self.founder)
        # Create 2 confirmed builder sections
        for section_type in [
            StartupBuilderSection.SectionType.PROBLEM,
            StartupBuilderSection.SectionType.CUSTOMER,
        ]:
            StartupBuilderSection.objects.create(
                owner=self.founder,
                startup_profile=self.profile,
                section_type=section_type,
                status=StartupBuilderSection.Status.CONFIRMED,
            )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        builder = response.data["builder"]
        self.assertEqual(builder["sections_confirmed"], 2)
        self.assertGreater(builder["completion_pct"], 0)

    def test_ownership_scope_enforced(self):
        other_user = User.objects.create_user(
            username="other_intel",
            email="other_intel@example.com",
            password="Password123!",
            role="founder",
        )
        other_profile = _make_profile(other_user, "Other Startup")
        self.client.force_authenticate(user=self.founder)
        response = self.client.get(self._url(profile=other_profile))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_recent_activity_includes_completed_milestones(self):
        self.client.force_authenticate(user=self.founder)
        _make_readiness(self.profile)
        _make_capital_plan(self.profile)
        _make_milestones(self.profile, n_complete=2, n_inprog=0)

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity = response.data["recent_activity"]
        types = [a["type"] for a in activity]
        self.assertIn("milestone_completed", types)
        self.assertIn("capital_plan_saved", types)

    def test_weakest_workspace_returns_capital_planner_for_critical_runway(self):
        self.client.force_authenticate(user=self.founder)
        _make_readiness(self.profile, score=80)
        StartupCapitalPlan.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            available_capital=Decimal("200000"),
            monthly_revenue=Decimal("0"),
            fixed_costs=Decimal("150000"),
            variable_costs=Decimal("60000"),
            net_burn=Decimal("210000"),
            runway_months=Decimal("0.9"),
            runway_status=StartupCapitalPlan.RunwayStatus.CRITICAL,
            scenarios={},
            allocations={},
            sensitivity={},
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["weakest_workspace"], "capital-planner")
