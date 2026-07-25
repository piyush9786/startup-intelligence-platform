from django.urls import path

from .views import HealthView, PlatformStatusView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("status/", PlatformStatusView.as_view(), name="platform-status"),
]
