from django.urls import path

from .views import (
    CookieTokenLogoutView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CurrentUserView,
    FounderRegistrationView,
)

urlpatterns = [
    path("register/", FounderRegistrationView.as_view(), name="founder-register"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("token/", CookieTokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token-refresh"),
    path("token/logout/", CookieTokenLogoutView.as_view(), name="token-logout"),
]
