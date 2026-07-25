from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .tracker_views import SchemeApplicationTrackerViewSet
from .verification_reviewer_views import (
    EligibilityVerificationReviewerDecisionCreateView,
    EligibilityVerificationReviewerEvidenceDownloadView,
    EligibilityVerificationReviewerQueueView,
)
from .verification_views import (
    EligibilityVerificationEvidenceUploadView,
    EligibilityVerificationGateListView,
    EligibilityVerificationSubmissionCreateView,
)
from .views import (
    EligibilityEvaluateView,
    RecommendationCurrentView,
    RecommendationGenerateView,
    RecommendationRunDetailView,
    RecommendationRunListView,
)

router = DefaultRouter()
router.register(
    r"tracker-applications",
    SchemeApplicationTrackerViewSet,
    basename="tracker-application",
)

urlpatterns = [
    path("eligibility/evaluate/", EligibilityEvaluateView.as_view(), name="eligibility-evaluate"),
    path(
        "eligibility/verifications/reviewer/submissions/",
        EligibilityVerificationReviewerQueueView.as_view(),
        name="eligibility-verification-reviewer-queue",
    ),
    path(
        "eligibility/verifications/reviewer/submissions/<uuid:submission_id>/decisions/",
        EligibilityVerificationReviewerDecisionCreateView.as_view(),
        name="eligibility-verification-reviewer-decision-create",
    ),
    path(
        "eligibility/verifications/reviewer/evidence/<uuid:evidence_id>/download/",
        EligibilityVerificationReviewerEvidenceDownloadView.as_view(),
        name="eligibility-verification-reviewer-evidence-download",
    ),
    path(
        "eligibility/verifications/gates/",
        EligibilityVerificationGateListView.as_view(),
        name="eligibility-verification-gate-list",
    ),
    path(
        "eligibility/verifications/submissions/",
        EligibilityVerificationSubmissionCreateView.as_view(),
        name="eligibility-verification-submission-create",
    ),
    path(
        "eligibility/verifications/submissions/<uuid:submission_id>/evidence/",
        EligibilityVerificationEvidenceUploadView.as_view(),
        name="eligibility-verification-evidence-upload",
    ),
    path("recommendations/generate/", RecommendationGenerateView.as_view(), name="recommendation-generate"),
    path("recommendations/current/", RecommendationCurrentView.as_view(), name="recommendation-current"),
    path("recommendations/runs/", RecommendationRunListView.as_view(), name="recommendation-run-list"),
    path("recommendations/runs/<uuid:run_id>/", RecommendationRunDetailView.as_view(), name="recommendation-run-detail"),
    path("", include(router.urls)),
]
