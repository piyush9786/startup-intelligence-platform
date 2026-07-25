from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.startups.models import StartupProfile
from apps.startups.services.verification_sandbox import (
    run_instant_verification_sandbox,
    validate_dpiit_number,
    validate_gstin_checksum,
)

User = get_user_model()


class InstantVerificationSandboxTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sandbox_user", password="password")
        self.profile = StartupProfile.objects.create(
            owner=self.user,
            startup_name="Sandbox Inc",
        )

    def test_gstin_validation(self):
        self.assertTrue(validate_gstin_checksum("27AAAAA0000A1Z5"))
        self.assertFalse(validate_gstin_checksum("INVALID_GSTIN"))

    def test_dpiit_validation(self):
        self.assertTrue(validate_dpiit_number("DPIIT12345"))
        self.assertTrue(validate_dpiit_number("DIPP/998877"))
        self.assertFalse(validate_dpiit_number("NO_PREFIX"))

    def test_run_sandbox_verification(self):
        res = run_instant_verification_sandbox(
            self.profile,
            field_name="gstin",
            field_value="27AAAAA0000A1Z5",
        )
        self.assertTrue(res["is_verified"])
        self.profile.refresh_from_db()
        self.assertIn("gstin", self.profile.verified_fields)
