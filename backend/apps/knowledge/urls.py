from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExtractKnowledgeView,
    KnowledgeExtractionRunViewSet,
    SchemeCandidateViewSet,
)

router = DefaultRouter()
router.register(
    "runs",
    KnowledgeExtractionRunViewSet,
    basename="knowledge-run",
)
router.register(
    "candidates",
    SchemeCandidateViewSet,
    basename="scheme-candidate",
)

urlpatterns = [
    path(
        "extract/",
        ExtractKnowledgeView.as_view(),
        name="extract-knowledge",
    ),
    *router.urls,
]
