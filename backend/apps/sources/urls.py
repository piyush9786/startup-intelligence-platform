from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CrawlRunViewSet,
    SourceDocumentViewSet,
    SourceViewSet,
)

router = DefaultRouter()
router.register("sources", SourceViewSet, basename="source")
router.register("source-documents", SourceDocumentViewSet, basename="source-document")
router.register("crawl-runs", CrawlRunViewSet, basename="crawl-run")

urlpatterns = [
    path("", include(router.urls)),
]
