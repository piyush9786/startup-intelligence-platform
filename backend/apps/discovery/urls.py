from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CrawlFrontierEntryViewSet,
    CrawlFrontierView,
    DiscoveredURLViewSet,
    DocumentQualityAssessmentViewSet,
)

router = DefaultRouter()
router.register("discovered-urls", DiscoveredURLViewSet, basename="discovered-url")
router.register("crawl-frontier", CrawlFrontierEntryViewSet, basename="crawl-frontier-entry")
router.register("document-quality", DocumentQualityAssessmentViewSet, basename="document-quality")

urlpatterns = [
    path("discovery/crawl/", CrawlFrontierView.as_view(), name="crawl-frontier"),
    path("", include(router.urls)),
]
