from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentChunkViewSet,
    DocumentExtractionViewSet,
    ProcessDocumentView,
)

router = DefaultRouter()
router.register("document-extractions", DocumentExtractionViewSet, basename="document-extraction")
router.register("document-chunks", DocumentChunkViewSet, basename="document-chunk")

urlpatterns = [
    path("documents/process/", ProcessDocumentView.as_view(), name="process-document"),
    path("", include(router.urls)),
]
