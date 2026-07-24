from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assistant.models import AgentSession
from apps.startups.models import StartupProfile

User = get_user_model()


class CopilotContextAPITests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="copilot_founder",
            email="copilot_founder@example.com",
            password="Password123!",
            role="founder",
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="Copilot Test Startup",
            stage="mvp",
            state="Karnataka",
        )

    def test_inject_copilot_context_creates_session_and_sets_workspace(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("assistant-chatbot-copilot-context")
        payload = {
            "workspace": "milestones",
            "context": {"milestone_count": 5, "completed": 2},
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["workspace"], "milestones")
        self.assertTrue(response.data["context_injected"])

        # Verify session has copilot_context set
        session = AgentSession.objects.filter(
            founder=self.founder,
            agent_type=AgentSession.AgentType.CHATBOT,
            status=AgentSession.Status.ACTIVE,
        ).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.copilot_context["workspace"], "milestones")
        self.assertEqual(session.copilot_context["context"]["milestone_count"], 5)

    def test_inject_copilot_context_for_capital_planner(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("assistant-chatbot-copilot-context")
        payload = {
            "workspace": "capital-planner",
            "context": {"runway_months": 14.5, "runway_status": "caution"},
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["workspace"], "capital-planner")

    def test_rejects_unknown_workspace_slug(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("assistant-chatbot-copilot-context")
        payload = {"workspace": "unknown-page-xyz"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("workspace", response.data)

    def test_copilot_context_workspace_response_reflects_milestones(self):
        """Chatbot responds with workspace-specific help when copilot_context is set."""
        from apps.assistant.services.chatbot import _platform_help_reply

        # Milestone-specific greeting should return platform_help intent
        # (using the workspace context approach)
        reply = _platform_help_reply(
            page_context={"current_view": "milestones"},
            copilot_context={"workspace": "milestones"},
        )
        self.assertIn("Execution & Milestones", reply.content)
        self.assertEqual(reply.navigation.view, "milestones")

    def test_copilot_context_capital_planner_reply(self):
        from apps.assistant.services.chatbot import _platform_help_reply

        reply = _platform_help_reply(
            page_context={"current_view": "capital-planner"},
            copilot_context={"workspace": "capital-planner"},
        )
        self.assertIn("Capital Planner", reply.content)
        self.assertEqual(reply.navigation.view, "capital-planner")

    def test_milestone_keyword_classify_intent(self):
        from apps.assistant.services.chatbot import _classify_intent

        self.assertEqual(_classify_intent("How do I set up a milestone dependency?"), "milestones")
        self.assertEqual(_classify_intent("What is my runway?"), "capital_planner")
        self.assertEqual(_classify_intent("Help me build a customer persona"), "builder")
