from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import SchemeApplicationTracker
from apps.schemes.models import Scheme, SchemeVersion
from apps.startups.models import StartupProfile

User = get_user_model()


class ApplicationTrackerAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tracker_user", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.profile = StartupProfile.objects.create(
            owner=self.user,
            startup_name="Tracker Startup",
            stage="validation",
        )
        self.scheme = Scheme.objects.create(
            canonical_name="Startup India Seed Fund",
        )
        self.scheme_version = SchemeVersion.objects.create(
            scheme=self.scheme,
            funding_amount="₹50 Lakhs",
            verification_status="verified",
        )

    def test_create_tracker_application(self):
        url = "/api/v1/tracker-applications/"
        data = {
            "startup_profile": str(self.profile.id),
            "scheme_version": str(self.scheme_version.id),
            "stage": "draft",
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SchemeApplicationTracker.objects.count(), 1)

    def test_generate_proposal_action(self):
        tracker = SchemeApplicationTracker.objects.create(
            owner=self.user,
            startup_profile=self.profile,
            scheme_version=self.scheme_version,
            stage="draft",
        )
        url = f"/api/v1/tracker-applications/{tracker.id}/generate-proposal/"
        res = self.client.post(url, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("proposal_title", res.data)
        self.assertEqual(res.data["startup_name"], "Tracker Startup")
