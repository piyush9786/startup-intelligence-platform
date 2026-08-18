from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .advisor_views import (
    StartupAdvisorBriefingCurrentView,
    StartupAdvisorBriefingDetailView,
    StartupAdvisorBriefingGenerateView,
    StartupAdvisorBriefingJobCurrentView,
    StartupAdvisorBriefingJobDetailView,
    StartupAdvisorBriefingListView,
    StartupAdvisorRecommendationSourceDownloadView,
    StartupAdvisorCurrentView,
    StartupAdvisorSnapshotGenerateView,
)
from .assessment_views import (
    StartupAssessmentDraftSubmitView,
    StartupAssessmentDraftViewSet,
)
from .builder_consultant_views import MasterConsultantGeneratorView
from .builder_views import (
    StartupBuilderSectionDetailView,
    StartupBuilderSectionDraftView,
    StartupBuilderSectionListView,
)
from .capital_planner_views import (
    StartupCapitalPlanCurrentView,
    StartupCapitalPlanGenerateView,
)
from .compliance_views import ComplianceRecordViewSet
from .expert_marketplace_views import ConsultationRequestViewSet
from .milestone_views import (
    StartupMilestoneCompleteView,
    StartupMilestoneDetailView,
    StartupMilestoneListCreateView,
    StartupMilestoneLogUpdateView,
)
from .onboarding_views import StartupOnboardingCurrentView
from .startup_intelligence_views import StartupIntelligenceView
from .startup_resume_views import StartupResumeGeneratorView
from .verification_sandbox_views import InstantVerificationSandboxView
from .views import (
    StartupFundingPlanCurrentView,
    StartupFundingPlanDetailView,
    StartupFundingPlanGenerateView,
    StartupFundingPlanListView,
    StartupProfileDocumentAutofillView,
    StartupProfileViewSet,
    StartupReadinessActionPlanCurrentView,
    StartupReadinessActionPlanDetailView,
    StartupReadinessActionPlanGenerateView,
    StartupReadinessActionPlanListView,
    StartupReadinessAssessmentDetailView,
    StartupReadinessAssessmentListView,
    StartupReadinessCurrentView,
    StartupReadinessEvaluateView,
    StartupStartingPlanCurrentView,
    StartupStartingPlanDetailView,
    StartupStartingPlanGenerateView,
    StartupStartingPlanListView,
)
from .workspace_views import (
    ApplicationStageEventViewSet,
    ApplicationTaskViewSet,
    ApplicationWorkflowViewSet,
    ConsultantProfileViewSet,
    FounderVaultDocumentViewSet,
)

router = DefaultRouter()
router.register("startup-profiles", StartupProfileViewSet, basename="startup-profile")
router.register("startup-assessment-drafts", StartupAssessmentDraftViewSet, basename="startup-assessment-draft")
router.register("compliance-records", ComplianceRecordViewSet, basename="compliance-record")
router.register("consultant-profiles", ConsultantProfileViewSet, basename="consultant-profile")
router.register("consultation-requests", ConsultationRequestViewSet, basename="consultation-request")
router.register("founder-vault-documents", FounderVaultDocumentViewSet, basename="founder-vault-document")
router.register("application-tasks", ApplicationTaskViewSet, basename="application-task")
router.register("application-stage-events", ApplicationStageEventViewSet, basename="application-stage-event")
router.register("application-workflows", ApplicationWorkflowViewSet, basename="application-workflow")

urlpatterns = [
    # Advisor
    path("startup-advisor/briefings/generate/", StartupAdvisorBriefingGenerateView.as_view(), name="startup-advisor-briefing-generate"),
    path("startup-advisor/briefings/jobs/current/", StartupAdvisorBriefingJobCurrentView.as_view(), name="startup-advisor-briefing-job-current"),
    path("startup-advisor/briefings/jobs/<uuid:job_id>/", StartupAdvisorBriefingJobDetailView.as_view(), name="startup-advisor-briefing-job-detail"),
    path("startup-advisor/briefings/current/", StartupAdvisorBriefingCurrentView.as_view(), name="startup-advisor-briefing-current"),
    path("startup-advisor/briefings/", StartupAdvisorBriefingListView.as_view(), name="startup-advisor-briefing-list"),
    path(
        "startup-advisor/briefings/<uuid:briefing_id>/recommendations/<uuid:recommendation_id>/source-download/",
        StartupAdvisorRecommendationSourceDownloadView.as_view(),
        name="startup-advisor-recommendation-source-download",
    ),
    path("startup-advisor/briefings/<uuid:briefing_id>/", StartupAdvisorBriefingDetailView.as_view(), name="startup-advisor-briefing-detail"),
    path("startup-advisor/current/", StartupAdvisorCurrentView.as_view(), name="startup-advisor-current"),
    path("startup-advisor/snapshots/generate/", StartupAdvisorSnapshotGenerateView.as_view(), name="startup-advisor-snapshot-generate"),

    # Onboarding & Profile
    path("startup-onboarding/current/", StartupOnboardingCurrentView.as_view(), name="startup-onboarding-current"),
    path("startup-profiles/autofill-from-document/", StartupProfileDocumentAutofillView.as_view(), name="startup-profile-autofill-from-document"),
    path("startup-assessment-drafts/<uuid:draft_id>/submit/", StartupAssessmentDraftSubmitView.as_view(), name="startup-assessment-draft-submit"),

    # Readiness
    path("startup-readiness/evaluate/", StartupReadinessEvaluateView.as_view(), name="startup-readiness-evaluate"),
    path("startup-readiness/current/", StartupReadinessCurrentView.as_view(), name="startup-readiness-current"),
    path("startup-readiness/assessments/", StartupReadinessAssessmentListView.as_view(), name="startup-readiness-assessment-list"),
    path("startup-readiness/assessments/<uuid:assessment_id>/", StartupReadinessAssessmentDetailView.as_view(), name="startup-readiness-assessment-detail"),
    path("startup-readiness/action-plans/generate/", StartupReadinessActionPlanGenerateView.as_view(), name="startup-readiness-action-plan-generate"),
    path("startup-readiness/action-plans/current/", StartupReadinessActionPlanCurrentView.as_view(), name="startup-readiness-action-plan-current"),
    path("startup-readiness/action-plans/", StartupReadinessActionPlanListView.as_view(), name="startup-readiness-action-plan-list"),
    path("startup-readiness/action-plans/<uuid:action_plan_id>/", StartupReadinessActionPlanDetailView.as_view(), name="startup-readiness-action-plan-detail"),

    # Funding & Starting plans
    path("startup-funding-plans/generate/", StartupFundingPlanGenerateView.as_view(), name="startup-funding-plan-generate"),
    path("startup-funding-plans/current/", StartupFundingPlanCurrentView.as_view(), name="startup-funding-plan-current"),
    path("startup-funding-plans/", StartupFundingPlanListView.as_view(), name="startup-funding-plan-list"),
    path("startup-funding-plans/<uuid:funding_plan_id>/", StartupFundingPlanDetailView.as_view(), name="startup-funding-plan-detail"),
    path("startup-starting-plans/generate/", StartupStartingPlanGenerateView.as_view(), name="startup-starting-plan-generate"),
    path("startup-starting-plans/current/", StartupStartingPlanCurrentView.as_view(), name="startup-starting-plan-current"),
    path("startup-starting-plans/", StartupStartingPlanListView.as_view(), name="startup-starting-plan-list"),
    path("startup-starting-plans/<uuid:starting_plan_id>/", StartupStartingPlanDetailView.as_view(), name="startup-starting-plan-detail"),

    # Builder
    path("startup-builder/generate-master-plan/", MasterConsultantGeneratorView.as_view(), name="startup-builder-generate-master-plan"),
    path("startup-builder/generate-resume/", StartupResumeGeneratorView.as_view(), name="startup-builder-generate-resume"),
    path("startup-builder/sections/", StartupBuilderSectionListView.as_view(), name="startup-builder-section-list"),
    path("startup-builder/sections/<str:section_type>/", StartupBuilderSectionDetailView.as_view(), name="startup-builder-section-detail"),
    path("startup-builder/sections/<str:section_type>/draft/", StartupBuilderSectionDraftView.as_view(), name="startup-builder-section-draft"),

    # Capital Plans & Milestones
    path("startup-capital-plans/current/", StartupCapitalPlanCurrentView.as_view(), name="startup-capital-plan-current"),
    path("startup-capital-plans/generate/", StartupCapitalPlanGenerateView.as_view(), name="startup-capital-plan-generate"),
    path("startup-milestones/", StartupMilestoneListCreateView.as_view(), name="startup-milestone-list-create"),
    path("startup-milestones/<uuid:milestone_id>/", StartupMilestoneDetailView.as_view(), name="startup-milestone-detail"),
    path("startup-milestones/<uuid:milestone_id>/complete/", StartupMilestoneCompleteView.as_view(), name="startup-milestone-complete"),
    path("startup-milestones/<uuid:milestone_id>/log-update/", StartupMilestoneLogUpdateView.as_view(), name="startup-milestone-log-update"),

    # Verification sandbox & Intelligence
    path("startups/verify-instant/", InstantVerificationSandboxView.as_view(), name="startup-verify-instant"),
    path("startups/<uuid:profile_id>/intelligence/", StartupIntelligenceView.as_view(), name="startup-intelligence"),

    path("", include(router.urls)),
]
