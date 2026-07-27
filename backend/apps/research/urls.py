"""URL configuration for research API endpoints."""
from django.urls import path

from .views import (
    CurrentResearchRequestView,
    ResearchRequestCreateView,
    ResearchRequestDetailView,
    StartupResearchReportDetailView,
    StartupResearchReportListView,
)

urlpatterns = [
    path("requests/", ResearchRequestCreateView.as_view(), name="research-request-create"),
    path(
        "requests/current/",
        CurrentResearchRequestView.as_view(),
        name="research-request-current",
    ),
    path("requests/<uuid:pk>/", ResearchRequestDetailView.as_view(), name="research-request-detail"),
    path("reports/", StartupResearchReportListView.as_view(), name="research-report-list"),
    path("reports/<uuid:pk>/", StartupResearchReportDetailView.as_view(), name="research-report-detail"),
]
