from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.core.views import HealthView, PlatformStatusView
from apps.discovery.views import (
    CrawlFrontierEntryViewSet,
    CrawlFrontierView,
    DiscoveredURLViewSet,
    DocumentQualityAssessmentViewSet,
)
from apps.documents.views import (
    DocumentChunkViewSet,
    DocumentExtractionViewSet,
    ProcessDocumentView,
)
from apps.recommendations.views import (
    EligibilityEvaluateView,
    RecommendationCurrentView,
    RecommendationGenerateView,
)
from apps.schemes.views import SchemeViewSet
from apps.sources.views import (
    CrawlRunViewSet,
    SourceDocumentViewSet,
    SourceViewSet,
)
from apps.startups.views import StartupProfileViewSet

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register(
    "source-documents",
    SourceDocumentViewSet,
    basename="source-document",
)
router.register("crawl-runs", CrawlRunViewSet, basename="crawl-run")
router.register(
    "document-extractions",
    DocumentExtractionViewSet,
    basename="document-extraction",
)
router.register(
    "document-chunks",
    DocumentChunkViewSet,
    basename="document-chunk",
)
router.register(
    "discovered-urls",
    DiscoveredURLViewSet,
    basename="discovered-url",
)
router.register(
    "crawl-frontier",
    CrawlFrontierEntryViewSet,
    basename="crawl-frontier-entry",
)
router.register(
    "document-quality",
    DocumentQualityAssessmentViewSet,
    basename="document-quality",
)
router.register("schemes", SchemeViewSet, basename="scheme")
router.register(
    "startup-profiles",
    StartupProfileViewSet,
    basename="startup-profile",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),
    path(
        "api/v1/health/",
        HealthView.as_view(),
        name="health",
    ),
    path(
        "api/v1/status/",
        PlatformStatusView.as_view(),
        name="platform-status",
    ),
    path(
        "api/v1/auth/token/",
        TokenObtainPairView.as_view(),
        name="token-obtain",
    ),
    path(
        "api/v1/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "api/v1/eligibility/evaluate/",
        EligibilityEvaluateView.as_view(),
        name="eligibility-evaluate",
    ),
    path(
        "api/v1/recommendations/generate/",
        RecommendationGenerateView.as_view(),
        name="recommendation-generate",
    ),
    path(
        "api/v1/recommendations/current/",
        RecommendationCurrentView.as_view(),
        name="recommendation-current",
    ),
    path(
        "api/v1/documents/process/",
        ProcessDocumentView.as_view(),
        name="process-document",
    ),
    path(
        "api/v1/discovery/crawl/",
        CrawlFrontierView.as_view(),
        name="crawl-frontier",
    ),
    path(
        "api/v1/knowledge/",
        include("apps.knowledge.urls"),
    ),
    path("api/v1/", include(router.urls)),
]
