from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.expert_marketplace_models import ConsultationRequest
from apps.startups.models import StartupProfile
from apps.startups.workspace_models import ConsultantProfile

User = get_user_model()


class ExpertMarketplaceAPITestCase(TestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="market-founder",
            email="market-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.other_founder = User.objects.create_user(
            username="other-market-founder",
            email="other-market-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.consultant_user = User.objects.create_user(
            username="market-consultant",
            email="market-consultant@example.com",
            password="Safe-password-2026!",
            role=User.Role.CONSULTANT,
            first_name="Asha",
            last_name="Mehta",
        )
        self.other_consultant_user = User.objects.create_user(
            username="other-consultant",
            email="other-consultant@example.com",
            password="Safe-password-2026!",
            role=User.Role.CONSULTANT,
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="Marketplace Startup",
            stage=StartupProfile.Stage.VALIDATION,
        )
        self.other_profile = StartupProfile.objects.create(
            owner=self.other_founder,
            startup_name="Other Marketplace Startup",
            stage=StartupProfile.Stage.IDEA,
        )
        self.consultant = ConsultantProfile.objects.create(
            user=self.consultant_user,
            headline="Government schemes and compliance advisor",
            bio="Supports founders with applications and renewals.",
            expertise=["DPIIT", "grants"],
            languages=["English", "Hindi"],
            states_served=["Maharashtra"],
            industries=["SaaS"],
            availability=ConsultantProfile.Availability.AVAILABLE,
            verification_status=ConsultantProfile.VerificationStatus.VERIFIED,
            is_public=True,
            years_experience=8,
        )
        self.other_consultant = ConsultantProfile.objects.create(
            user=self.other_consultant_user,
            headline="Finance advisor",
            availability=ConsultantProfile.Availability.AVAILABLE,
            verification_status=ConsultantProfile.VerificationStatus.VERIFIED,
            is_public=True,
        )
        self.founder_client = APIClient()
        self.founder_client.force_authenticate(user=self.founder)

    def create_request(self):
        response = self.founder_client.post(
            "/api/v1/consultation-requests/",
            {
                "startup_profile": str(self.profile.id),
                "consultant": str(self.consultant.id),
                "topic": "DPIIT renewal strategy",
                "message": "Help us prepare the renewal evidence.",
                "preferred_date": str(timezone.localdate() + timedelta(days=7)),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return ConsultationRequest.objects.get(pk=response.data["id"])

    def test_founder_can_request_verified_available_consultant(self):
        consultation = self.create_request()
        self.assertEqual(consultation.founder, self.founder)
        self.assertEqual(consultation.status, ConsultationRequest.Status.REQUESTED)
        self.assertEqual(consultation.startup_profile, self.profile)
        self.assertEqual(consultation.consultant, self.consultant)

    def test_requests_are_visible_only_to_participants(self):
        self.create_request()

        other_founder_client = APIClient()
        other_founder_client.force_authenticate(user=self.other_founder)
        founder_list = other_founder_client.get("/api/v1/consultation-requests/")
        self.assertEqual(founder_list.status_code, status.HTTP_200_OK)
        self.assertEqual(founder_list.data["count"], 0)

        other_consultant_client = APIClient()
        other_consultant_client.force_authenticate(user=self.other_consultant_user)
        consultant_list = other_consultant_client.get(
            "/api/v1/consultation-requests/"
        )
        self.assertEqual(consultant_list.status_code, status.HTTP_200_OK)
        self.assertEqual(consultant_list.data["count"], 0)

        target_client = APIClient()
        target_client.force_authenticate(user=self.consultant_user)
        target_list = target_client.get("/api/v1/consultation-requests/")
        self.assertEqual(target_list.status_code, status.HTTP_200_OK)
        self.assertEqual(target_list.data["count"], 1)

    def test_consultant_can_accept_schedule_and_complete_request(self):
        consultation = self.create_request()
        consultant_client = APIClient()
        consultant_client.force_authenticate(user=self.consultant_user)

        accepted = consultant_client.post(
            f"/api/v1/consultation-requests/{consultation.id}/respond/",
            {
                "status": "accepted",
                "consultant_response": "I can help with this renewal.",
            },
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)

        scheduled_for = timezone.now() + timedelta(days=2)
        scheduled = consultant_client.post(
            f"/api/v1/consultation-requests/{consultation.id}/respond/",
            {
                "status": "scheduled",
                "scheduled_for": scheduled_for.isoformat(),
                "consultant_response": "Session confirmed.",
            },
            format="json",
        )
        self.assertEqual(scheduled.status_code, status.HTTP_200_OK)

        completed = consultant_client.post(
            f"/api/v1/consultation-requests/{consultation.id}/respond/",
            {
                "status": "completed",
                "consultant_response": "Renewal plan delivered.",
            },
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        consultation.refresh_from_db()
        self.consultant.refresh_from_db()
        self.assertEqual(consultation.status, ConsultationRequest.Status.COMPLETED)
        self.assertEqual(self.consultant.sessions_completed, 1)

    def test_founder_can_cancel_open_request(self):
        consultation = self.create_request()
        cancelled = self.founder_client.post(
            f"/api/v1/consultation-requests/{consultation.id}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, ConsultationRequest.Status.CANCELLED)

    def test_unverified_or_unavailable_consultants_are_rejected(self):
        self.consultant.availability = ConsultantProfile.Availability.UNAVAILABLE
        self.consultant.save(update_fields=["availability", "updated_at"])
        response = self.founder_client.post(
            "/api/v1/consultation-requests/",
            {
                "startup_profile": str(self.profile.id),
                "consultant": str(self.consultant.id),
                "topic": "Funding review",
                "message": "Please review our application.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_founder_cannot_request_for_another_startup(self):
        response = self.founder_client.post(
            "/api/v1/consultation-requests/",
            {
                "startup_profile": str(self.other_profile.id),
                "consultant": str(self.consultant.id),
                "topic": "Compliance review",
                "message": "Please review this startup.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
