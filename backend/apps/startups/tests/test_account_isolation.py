from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.recommendations.verification_views import (
    _visible_profiles as verification_visible_profiles,
)
from apps.recommendations.views import (
    _visible_profiles as recommendation_visible_profiles,
)
from apps.startups.advisor_views import (
    _visible_profiles as advisor_visible_profiles,
)
from apps.startups.models import StartupProfile
from apps.startups.views import (
    _visible_profiles as startup_visible_profiles,
)

User = get_user_model()


class FounderAccountIsolationTests(APITestCase):
    def setUp(self):
        self.account = User.objects.create_user(
            username="staff-founder",
            email="staff-founder@example.com",
            password="Password123!",
            role="founder",
            is_staff=False,
        )
        self.other_account = User.objects.create_user(
            username="other-founder",
            email="other-founder@example.com",
            password="Password123!",
            role="founder",
        )

        self.owned_profile = StartupProfile.objects.create(
            owner=self.account,
            startup_name="Owned Startup",
        )
        self.foreign_profile = StartupProfile.objects.create(
            owner=self.other_account,
            startup_name="Foreign Startup",
        )

    def test_staff_flag_does_not_expand_founder_visibility(self):
        visibility_functions = (
            startup_visible_profiles,
            advisor_visible_profiles,
            recommendation_visible_profiles,
            verification_visible_profiles,
        )

        for visibility_function in visibility_functions:
            with self.subTest(
                visibility_function=visibility_function.__module__,
            ):
                visible_ids = set(
                    visibility_function(self.account)
                    .values_list("id", flat=True)
                )

                self.assertEqual(
                    visible_ids,
                    {self.owned_profile.id},
                )

    def test_profile_list_contains_only_authenticated_owner(self):
        self.client.force_authenticate(user=self.account)

        response = self.client.get(
            reverse("startup-profile-list"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        payload = response.data
        records = (
            payload.get("results", [])
            if isinstance(payload, dict)
            else payload
        )

        returned_ids = {
            str(record["id"])
            for record in records
        }

        self.assertEqual(
            returned_ids,
            {str(self.owned_profile.id)},
        )

    def test_foreign_profile_detail_returns_not_found(self):
        self.client.force_authenticate(user=self.account)

        response = self.client.get(
            reverse(
                "startup-profile-detail",
                kwargs={
                    "pk": self.foreign_profile.id,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_foreign_advisor_workspace_returns_not_found(self):
        self.client.force_authenticate(user=self.account)

        response = self.client.get(
            reverse("startup-advisor-current"),
            {
                "startup_profile_id":
                    str(self.foreign_profile.id),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_empty_account_is_not_given_demo_startup_data(self):
        empty_account = User.objects.create_user(
            username="empty-founder",
            email="empty-founder@example.com",
            password="Password123!",
            role="founder",
        )

        self.client.force_authenticate(
            user=empty_account,
        )

        response = self.client.get(
            reverse("startup-profile-list"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            StartupProfile.objects.filter(
                owner=empty_account,
            ).exists(),
        )
