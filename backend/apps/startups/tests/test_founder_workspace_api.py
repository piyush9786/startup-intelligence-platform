from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import SchemeApplicationTracker
from apps.schemes.models import Authority, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument
from apps.startups.models import StartupProfile
from apps.startups.workspace_models import (
    ApplicationStageEvent,
    ApplicationTask,
    ComplianceRecord,
    ConsultantProfile,
    FounderVaultDocument,
)

User = get_user_model()


class FounderWorkspaceAPITestCase(TestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="workspace-founder",
            email="workspace-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.other_founder = User.objects.create_user(
            username="other-founder",
            email="other-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.consultant = User.objects.create_user(
            username="verified-consultant",
            email="consultant@example.com",
            password="Safe-password-2026!",
            role=User.Role.CONSULTANT,
            first_name="Asha",
            last_name="Mehta",
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="Workspace Startup",
            stage=StartupProfile.Stage.VALIDATION,
        )
        self.other_profile = StartupProfile.objects.create(
            owner=self.other_founder,
            startup_name="Other Startup",
            stage=StartupProfile.Stage.IDEA,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.founder)

        authority = Authority.objects.create(name="Workspace Authority")
        scheme = Scheme.objects.create(
            canonical_name="Workspace Support Scheme",
            authority=authority,
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        )
        source = Source.objects.create(
            name="Workspace Scheme Source",
            official_domain="workspace-scheme.gov.in",
            listing_url="https://workspace-scheme.gov.in",
        )
        source_document = SourceDocument.objects.create(
            source=source,
            source_url="https://workspace-scheme.gov.in/notification",
            content_hash="workspace-source-hash",
            retrieved_at=timezone.now(),
        )
        self.scheme_version = SchemeVersion.objects.create(
            scheme=scheme,
            version_number=1,
            source_document=source_document,
            captured_at=timezone.now(),
            content_hash="workspace-version-hash",
            official_url="https://workspace-scheme.gov.in/apply",
            verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        )
        self.application = SchemeApplicationTracker.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            scheme_version=self.scheme_version,
            stage=SchemeApplicationTracker.Stage.DRAFT,
        )

    def test_compliance_records_are_owner_scoped(self):
        response = self.client.post(
            "/api/v1/compliance-records/",
            {
                "startup_profile": str(self.profile.id),
                "compliance_type": "dpiit",
                "title": "DPIIT recognition",
                "status": "active",
                "registration_number": "DIPP-1001",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ComplianceRecord.objects.count(), 1)

        rejected = self.client.post(
            "/api/v1/compliance-records/",
            {
                "startup_profile": str(self.other_profile.id),
                "compliance_type": "gst",
                "title": "GST registration",
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.other_founder)
        listed = self.client.get("/api/v1/compliance-records/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["count"], 0)

    def test_consultant_directory_exposes_public_profiles(self):
        consultant_client = APIClient()
        consultant_client.force_authenticate(user=self.consultant)
        created = consultant_client.post(
            "/api/v1/consultant-profiles/",
            {
                "headline": "Government schemes and compliance advisor",
                "bio": "Supports early-stage founders.",
                "expertise": ["DPIIT", "grants"],
                "languages": ["English", "Hindi", "Marathi"],
                "states_served": ["Maharashtra"],
                "industries": ["SaaS"],
                "availability": "available",
                "is_public": True,
                "years_experience": 8,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConsultantProfile.objects.count(), 1)

        listed = self.client.get("/api/v1/consultant-profiles/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["display_name"], "Asha Mehta")

    def test_application_tasks_and_stage_events_are_owner_scoped(self):
        created = self.client.post(
            "/api/v1/application-tasks/",
            {
                "application": str(self.application.id),
                "title": "Upload audited financial statements",
                "status": "todo",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ApplicationTask.objects.count(), 1)

        transitioned = self.client.post(
            f"/api/v1/application-workflows/{self.application.id}/transition/",
            {
                "stage": "submitted",
                "note": "Submitted on the official portal.",
            },
            format="json",
        )
        self.assertEqual(transitioned.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(
            self.application.stage,
            SchemeApplicationTracker.Stage.SUBMITTED,
        )
        event = ApplicationStageEvent.objects.get()
        self.assertEqual(event.from_stage, "draft")
        self.assertEqual(event.to_stage, "submitted")

        self.client.force_authenticate(user=self.other_founder)
        hidden_tasks = self.client.get("/api/v1/application-tasks/")
        hidden_events = self.client.get("/api/v1/application-stage-events/")
        self.assertEqual(hidden_tasks.data["count"], 0)
        self.assertEqual(hidden_events.data["count"], 0)

    @patch("apps.startups.workspace_serializers.upload_stream")
    def test_vault_upload_is_owned_by_authenticated_founder(self, upload_stream):
        uploaded = SimpleUploadedFile(
            "certificate.pdf",
            b"vault-document-content",
            content_type="application/pdf",
        )
        response = self.client.post(
            "/api/v1/founder-vault-documents/",
            {
                "startup_profile": str(self.profile.id),
                "title": "DPIIT certificate",
                "category": "compliance",
                "file": uploaded,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        upload_stream.assert_called_once()
        document = FounderVaultDocument.objects.get()
        self.assertEqual(document.owner, self.founder)
        self.assertEqual(document.startup_profile, self.profile)

        self.client.force_authenticate(user=self.other_founder)
        listed = self.client.get("/api/v1/founder-vault-documents/")
        self.assertEqual(listed.data["count"], 0)
