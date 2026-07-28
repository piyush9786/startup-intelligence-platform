import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_logout_blacklists_http_only_refresh_token():
    User.objects.create_user(
        username="logout-founder",
        email="logout-founder@example.com",
        password="Safe-test-password-2026!",
    )
    client = APIClient()
    login_response = client.post(
        reverse("token-obtain"),
        {
            "username": "logout-founder",
            "password": "Safe-test-password-2026!",
        },
        format="json",
    )

    assert login_response.status_code == status.HTTP_200_OK
    assert "refresh" not in login_response.data
    refresh = RefreshToken(login_response.cookies["refresh_token"].value)

    logout_response = client.post(reverse("token-logout"), {}, format="json")

    assert logout_response.status_code == status.HTTP_200_OK
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
    assert logout_response.cookies["refresh_token"]["max-age"] == 0

