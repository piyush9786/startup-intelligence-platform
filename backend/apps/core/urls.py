from django.urls import path

from .views import AIReadinessView, HealthView, PlatformStatusView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("ai-readiness/", AIReadinessView.as_view(), name="ai-readiness"),
    path("status/", PlatformStatusView.as_view(), name="platform-status"),
]
