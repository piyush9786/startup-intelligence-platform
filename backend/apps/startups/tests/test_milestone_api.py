from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.startups.models import StartupMilestone, StartupProfile

User = get_user_model()


class MilestoneAPITests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="milestone_founder",
            email="milestone_founder@example.com",
            password="Password123!",
            role="founder",
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="AeroDynamics Corp",
            stage="mvp",
            state="Karnataka",
        )

    def test_list_milestones_empty(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("startup-milestone-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"milestones": []})

    def test_create_milestone(self):
        self.client.force_authenticate(user=self.founder)
        url = reverse("startup-milestone-list-create")
        payload = {
            "title": "Build Flight Sensor MVP",
            "description": "Construct initial sensor prototype for wind tunnel test.",
            "category": "product",
            "target_date": "2026-10-15",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Build Flight Sensor MVP")
        self.assertEqual(response.data["status"], "pending")

    def test_dependency_enforcement_and_completion(self):
        self.client.force_authenticate(user=self.founder)
        m1 = StartupMilestone.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            title="Complete Wind Tunnel Bench Test",
            category="product",
            status="pending",
        )
        m2 = StartupMilestone.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            title="Deploy Flight Software to Field",
            category="product",
            status="pending",
        )
        m2.dependencies.add(m1)

        # Attempt to complete m2 while m1 is incomplete -> HTTP 400
        complete_url_m2 = reverse(
            "startup-milestone-complete",
            kwargs={"milestone_id": m2.id},
        )
        resp_blocked = self.client.post(
            complete_url_m2,
            {"evidence": {"note": "Field deployment attempted"}},
            format="json",
        )
        self.assertEqual(resp_blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Prerequisite milestones are incomplete", resp_blocked.data["detail"])

        # Complete m1
        complete_url_m1 = reverse(
            "startup-milestone-complete",
            kwargs={"milestone_id": m1.id},
        )
        resp_m1 = self.client.post(
            complete_url_m1,
            {"evidence": {"lab_results": "Passed 99.8% precision"}},
            format="json",
        )
        self.assertEqual(resp_m1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_m1.data["status"], "completed")

        # Now complete m2 -> HTTP 200
        resp_m2 = self.client.post(
            complete_url_m2,
            {"evidence": {"field_site": "Hindustan Aeronautics Field"}},
            format="json",
        )
        self.assertEqual(resp_m2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_m2.data["status"], "completed")

    def test_log_update(self):
        self.client.force_authenticate(user=self.founder)
        m1 = StartupMilestone.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            title="Secure Seed Grant",
            category="funding",
        )
        url = reverse(
            "startup-milestone-log-update",
            kwargs={"milestone_id": m1.id},
        )
        payload = {"note": "Submitted application to NITI Aayog."}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["updates_log"]), 1)
        self.assertEqual(
            response.data["updates_log"][0]["note"],
            "Submitted application to NITI Aayog.",
        )
