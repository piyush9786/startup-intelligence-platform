from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    CurrentUserView,
    FounderRegistrationView,
)

urlpatterns = [
    path("register/", FounderRegistrationView.as_view(), name="founder-register"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
