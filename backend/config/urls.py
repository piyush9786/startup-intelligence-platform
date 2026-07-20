from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.views import HealthView, PlatformStatusView
from apps.recommendations.views import EligibilityEvaluateView
from apps.schemes.views import SchemeViewSet
from apps.sources.views import CrawlRunViewSet, SourceDocumentViewSet, SourceViewSet
from apps.startups.views import StartupProfileViewSet

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register(
    "source-documents",
    SourceDocumentViewSet,
    basename="source-document",
)
router.register("crawl-runs", CrawlRunViewSet, basename="crawl-run")
router.register("schemes", SchemeViewSet, basename="scheme")
router.register(
    "startup-profiles",
    StartupProfileViewSet,
    basename="startup-profile",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/status/", PlatformStatusView.as_view(), name="platform-status"),
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
    path("api/v1/", include(router.urls)),
]
