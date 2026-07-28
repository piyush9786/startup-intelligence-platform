from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.startups.models import StartupProfile
from apps.startups.services.builder_draft_service import BuilderDraftResult

User = get_user_model()


class StartupBuilderAPITests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="builder_founder",
            email="builder_founder@example.com",
            password="Password123!",
            role="founder",
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="AeroBuild Systems",
            stage="mvp",
            state="Karnataka",
            sectors=["aerospace", "hardware"],
            dpiit_recognized=True,
        )

    def test_unauthenticated_request_denied(self):
        url = reverse("startup-builder-section-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_sections_empty_when_none_persisted(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("startup-builder-section-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"sections": []})

    def test_get_section_default_when_not_created(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse(
            "startup-builder-section-detail",
            kwargs={"section_type": "problem"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["section_type"], "problem")
        self.assertEqual(response.data["status"], "draft")
        self.assertEqual(response.data["content"], {})

    def test_put_section_draft_and_confirm(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse(
            "startup-builder-section-detail",
            kwargs={"section_type": "problem"},
        )
        payload = {
            "content": {
                "problem_statement": "Drone payload accuracy is poor under high wind.",
                "who_has_this_problem": "Defense and surveying drone operators.",
                "current_alternatives": "Manual gyro stabilization.",
                "why_now": "New MEMS sensors enable real-time compensation.",
                "evidence_of_problem": "30% packet loss in field trials.",
            },
            "confirm": False,
        }
        response = self.client.put(url, payload, format="json")
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertEqual(response.data["status"], "draft")

        # Now confirm section
        confirm_payload = {
            "content": payload["content"],
            "confirm": True,
        }
        response = self.client.put(url, confirm_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "confirmed")
        self.assertIsNotNone(response.data["confirmed_at"])

    def test_generate_ai_draft_success(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse(
            "startup-builder-section-draft",
            kwargs={"section_type": "customer"},
        )
        mock_result = BuilderDraftResult(
            section_type="customer",
            draft={
                "primary_customer_segment": "Defense drone integrators",
                "customer_profile": "Tier-1 aerospace suppliers in India",
                "customer_pain_intensity": "High — mission failure risk",
                "customer_willingness_to_pay": "High — $10k+ per unit",
                "reach_channels": "DPIIT defense tech expos & direct sales",
            },
            prompt_version="builder-draft-v1",
            model_name="qwen3.5:9b",
            provider="ollama",
        )

        with patch(
            "apps.startups.builder_views.generate_builder_section_draft",
            return_value=mock_result,
        ):
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], "ai_drafted")
            self.assertEqual(
                response.data["ai_draft"]["primary_customer_segment"],
                "Defense drone integrators",
            )
