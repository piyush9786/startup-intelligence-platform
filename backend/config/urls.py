from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin & Documentation
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Modular App Routing (all prefixed under /api/v1/)
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/assistant/", include("apps.assistant.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.discovery.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/knowledge/", include("apps.knowledge.urls")),
    path("api/v1/", include("apps.recommendations.urls")),
    path("api/v1/", include("apps.schemes.urls")),
    path("api/v1/", include("apps.sources.urls")),
    path("api/v1/", include("apps.startups.urls")),
]
