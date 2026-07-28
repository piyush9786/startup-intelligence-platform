from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import SchemeApplicationTracker
from apps.schemes.models import Authority, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument
from apps.startups.models import StartupProfile
from apps.startups.workspace_models import ApplicationStageEvent

User = get_user_model()


class TrackerStageIntegrityTestCase(TestCase):
    def setUp(self):
        self.founder = User.objects.create_user(
            username="pipeline-founder",
            email="pipeline-founder@example.com",
            password="Safe-password-2026!",
            role=User.Role.FOUNDER,
        )
        self.profile = StartupProfile.objects.create(
            owner=self.founder,
            startup_name="Pipeline Startup",
            stage=StartupProfile.Stage.VALIDATION,
        )
        authority = Authority.objects.create(name="Pipeline Authority")
        scheme = Scheme.objects.create(
            canonical_name="Pipeline Support Scheme",
            authority=authority,
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        )
        source = Source.objects.create(
            name="Pipeline Scheme Source",
            official_domain="pipeline.gov.in",
            listing_url="https://pipeline.gov.in",
        )
        source_document = SourceDocument.objects.create(
            source=source,
            source_url="https://pipeline.gov.in/notification",
            content_hash="pipeline-source-hash",
            retrieved_at=timezone.now(),
        )
        self.scheme_version = SchemeVersion.objects.create(
            scheme=scheme,
            version_number=1,
            source_document=source_document,
            captured_at=timezone.now(),
            content_hash="pipeline-version-hash",
            official_url="https://pipeline.gov.in/apply",
            verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.founder)

    def create_tracker(self):
        return SchemeApplicationTracker.objects.create(
            owner=self.founder,
            startup_profile=self.profile,
            scheme_version=self.scheme_version,
            stage=SchemeApplicationTracker.Stage.DRAFT,
        )

    def test_creation_always_starts_in_draft(self):
        response = self.client.post(
            "/api/v1/tracker-applications/",
            {
                "startup_profile": str(self.profile.id),
                "scheme_version": str(self.scheme_version.id),
                "stage": "approved",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["stage"], "draft")
        tracker = SchemeApplicationTracker.objects.get(id=response.data["id"])
        self.assertEqual(tracker.stage, SchemeApplicationTracker.Stage.DRAFT)

    def test_direct_stage_patch_is_rejected_without_history(self):
        tracker = self.create_tracker()

        response = self.client.patch(
            f"/api/v1/tracker-applications/{tracker.id}/",
            {"stage": "submitted"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", response.data)
        tracker.refresh_from_db()
        self.assertEqual(tracker.stage, SchemeApplicationTracker.Stage.DRAFT)
        self.assertFalse(ApplicationStageEvent.objects.exists())

    def test_workflow_transition_changes_stage_and_writes_event(self):
        tracker = self.create_tracker()

        response = self.client.post(
            f"/api/v1/application-workflows/{tracker.id}/transition/",
            {
                "stage": "submitted",
                "note": "Submitted on the official portal.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tracker.refresh_from_db()
        self.assertEqual(tracker.stage, SchemeApplicationTracker.Stage.SUBMITTED)
        self.assertIsNotNone(tracker.submitted_at)

        event = ApplicationStageEvent.objects.get(application=tracker)
        self.assertEqual(event.from_stage, "draft")
        self.assertEqual(event.to_stage, "submitted")
        self.assertEqual(event.created_by, self.founder)
