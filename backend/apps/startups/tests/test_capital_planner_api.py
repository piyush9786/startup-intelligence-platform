from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.startups.models import StartupProfile
from apps.startups.services.capital_planner_engine import (
    build_capital_scenarios,
    calculate_capital_metrics,
)

User = get_user_model()


class CapitalPlannerAPITests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="capital_founder",
            email="capital_founder@example.com",
            password="Password123!",
            role="founder",
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="PayTech Solutions",
            stage="early_revenue",
            state="Maharashtra",
            sectors=["fintech"],
        )

    def test_calculation_engine_metrics(self):
        metrics = calculate_capital_metrics(
            available_capital=1200000,
            monthly_revenue=200000,
            fixed_costs=250000,
            variable_costs=50000,
        )
        self.assertEqual(metrics["net_burn"], 100000.0)
        self.assertEqual(metrics["runway_months"], 12.0)
        self.assertEqual(metrics["runway_status"], "caution")

        scenarios = build_capital_scenarios(metrics)
        self.assertIn("conservative", scenarios)
        self.assertIn("balanced", scenarios)
        self.assertIn("growth", scenarios)
        self.assertGreater(scenarios["conservative"]["runway_months"], metrics["runway_months"])

    def test_current_capital_plan_404_when_none_exists(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("startup-capital-plan-current")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generate_capital_plan(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("startup-capital-plan-generate")
        payload = {
            "available_capital": 2400000,
            "monthly_revenue": 300000,
            "fixed_costs": 400000,
            "variable_costs": 100000,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["net_burn"], "200000.00")
        self.assertEqual(response.data["runway_months"], "12.0")
        self.assertEqual(response.data["runway_status"], "caution")
        self.assertIn("scenarios", response.data)
        self.assertIn("allocations", response.data)
        self.assertIn("sensitivity", response.data)
        self.assertIn("ai_explanation", response.data)

        # Confirm retrieval of current capital plan
        current_url = reverse("startup-capital-plan-current")
        current_resp = self.client.get(current_url)
        self.assertEqual(current_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(current_resp.data["id"], response.data["id"])
