from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupProfile

User = get_user_model()


class StartupResumeGeneratorAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="resume_user", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.profile = StartupProfile.objects.create(
            owner=self.user,
            startup_name="AgriCold Tech",
            stage="mvp",
        )

    def test_generate_startup_resume_api(self):
        url = "/api/v1/startup-builder/generate-resume/"
        data = {
            "idea_description": (
                "Farm-to-retail cold chain supply logistics for smallholder "
                "Indian farmers"
            ),
            "sector": "AgriTech",
            "funding_required": "₹30 Lakhs",
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("resume_header", res.data)
        self.assertIn("executive_summary", res.data)
        self.assertIn("core_pillars", res.data)
        self.assertIn("matched_schemes", res.data)
        self.assertIn("execution_roadmap", res.data)
        self.assertIn("consultant_insights", res.data)
        self.assertEqual(res.data["generator_version"], "startup-executive-resume-v2")
