from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupProfile

User = get_user_model()


class MasterConsultantGeneratorAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="consultant_user", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.profile = StartupProfile.objects.create(
            owner=self.user,
            startup_name="Medical Drone Logistics",
            stage="prototype",
        )

    def test_generate_master_plan_api(self):
        url = "/api/v1/startup-builder/generate-master-plan/"
        data = {
            "idea_description": (
                "AI-powered drone delivery network for urgent medical "
                "vaccines in rural India"
            ),
            "sector": "HealthTech / Logistics",
            "funding_required": "₹50 Lakhs",
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("generated_title", res.data)
        self.assertIn("idea_understanding", res.data)
        self.assertIn("business_plan", res.data)
        self.assertIn("recommended_schemes", res.data)
        self.assertIn("execution_roadmap", res.data)
        self.assertIn("consultant_recommendations", res.data)
        self.assertTrue(res.data["generated_by"].startswith("ai-startup-consultant"))
