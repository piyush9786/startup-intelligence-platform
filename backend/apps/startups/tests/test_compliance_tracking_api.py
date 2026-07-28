from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupProfile
from apps.startups.workspace_models import ComplianceRecord

User = get_user_model()


class ComplianceTrackingAPITestCase(TestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="compliance-founder",
            email="compliance-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="Compliance Startup",
            stage=StartupProfile.Stage.VALIDATION,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.founder)

    def create_record(self, *, title, expires_on, reminder_days=30, status_value="active"):
        return ComplianceRecord.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            compliance_type=ComplianceRecord.ComplianceType.OTHER,
            title=title,
            status=status_value,
            expires_on=expires_on,
            renewal_reminder_days=reminder_days,
        )

    def test_summary_uses_effective_status_and_each_record_reminder_window(self):
        today = timezone.localdate()
        self.create_record(
            title="Expired registration",
            expires_on=today - timedelta(days=1),
            reminder_days=30,
        )
        due = self.create_record(
            title="Renewal due",
            expires_on=today + timedelta(days=5),
            reminder_days=10,
        )
        self.create_record(
            title="Renewal later",
            expires_on=today + timedelta(days=20),
            reminder_days=10,
        )

        response = self.client.get(
            "/api/v1/compliance-records/summary/",
            {"startup_profile": str(self.profile.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "total": 3,
                "active": 2,
                "expired": 1,
                "expiring_within_30_days": 2,
                "renewal_due": 1,
                "in_progress": 0,
            },
        )

        detail = self.client.get(f"/api/v1/compliance-records/{due.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertTrue(detail.data["renewal_due"])
        self.assertEqual(
            detail.data["reminder_starts_on"],
            today - timedelta(days=5),
        )

    def test_reminder_days_are_bounded(self):
        response = self.client.post(
            "/api/v1/compliance-records/",
            {
                "startup_profile": str(self.profile.id),
                "compliance_type": "dpiit",
                "title": "DPIIT recognition",
                "renewal_reminder_days": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("renewal_reminder_days", response.data)

    def test_compliance_records_support_update_and_delete(self):
        created = self.client.post(
            "/api/v1/compliance-records/",
            {
                "startup_profile": str(self.profile.id),
                "compliance_type": "udyam",
                "title": "Udyam registration",
                "status": "in_progress",
                "renewal_reminder_days": 45,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        record_id = created.data["id"]
        updated = self.client.patch(
            f"/api/v1/compliance-records/{record_id}/",
            {
                "status": "active",
                "registration_number": "UDYAM-MH-00-0000001",
            },
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["status"], "active")
        self.assertEqual(
            updated.data["registration_number"],
            "UDYAM-MH-00-0000001",
        )

        deleted = self.client.delete(
            f"/api/v1/compliance-records/{record_id}/"
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ComplianceRecord.objects.filter(id=record_id).exists())
