from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExternalCapitalSupportRecordViewSet,
    ExternalCertificationRequirementRecordViewSet,
    ExternalSchemeRecordViewSet,
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


router.register(
    "external-schemes",
    ExternalSchemeRecordViewSet,
    basename="external-scheme",
)

router.register(
    "external-capital-support",
    ExternalCapitalSupportRecordViewSet,
    basename="external-capital-support",
)
router.register(
    "external-certification-requirements",
    ExternalCertificationRequirementRecordViewSet,
    basename="external-certification-requirement",
)

urlpatterns = [
    path(
        "extract/",
        ExtractKnowledgeView.as_view(),
        name="extract-knowledge",
    ),
    *router.urls,
]
