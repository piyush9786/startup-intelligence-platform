from django.shortcuts import get_object_or_404
from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.recommendations.serializers import RecommendationSerializer

from .models import StartupAssessmentDraft
from .serializers import (
    StartupAssessmentDraftCreateSerializer,
    StartupAssessmentDraftSerializer,
    StartupAssessmentDraftSubmitRequestSerializer,
    StartupAssessmentDraftUpdateSerializer,
    StartupProfileSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
)
from .services.assessment_submission import (
    AssessmentDraftAlreadySubmittedError,
    submit_startup_assessment_draft,
)


def _visible_assessment_drafts(user):
    queryset = StartupAssessmentDraft.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
    return queryset


class StartupAssessmentDraftViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "startup_profile"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return _visible_assessment_drafts(self.request.user).select_related(
            "owner",
            "startup_profile",
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StartupAssessmentDraftCreateSerializer
        if self.action in {"update", "partial_update"}:
            return StartupAssessmentDraftUpdateSerializer
        return StartupAssessmentDraftSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft = serializer.save()
        response_status = status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK
        return Response(
            StartupAssessmentDraftSerializer(
                draft,
                context=self.get_serializer_context(),
            ).data,
            status=response_status,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        draft = serializer.save()
        return Response(
            StartupAssessmentDraftSerializer(
                draft,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_200_OK,
        )


class StartupAssessmentDraftSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):
        request_serializer = StartupAssessmentDraftSubmitRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        draft = get_object_or_404(
            _visible_assessment_drafts(request.user).select_related(
                "owner",
                "startup_profile",
            ),
            pk=draft_id,
        )

        try:
            submission = submit_startup_assessment_draft(
                draft=draft,
                requested_by=request.user,
            )
        except AssessmentDraftAlreadySubmittedError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        generation = submission.recommendation_generation
        recommendations = RecommendationSerializer(
            generation.recommendations,
            many=True,
        ).data

        return Response(
            {
                "draft": StartupAssessmentDraftSerializer(
                    submission.draft,
                    context={"request": request},
                ).data,
                "startup_profile": StartupProfileSerializer(
                    submission.startup_profile,
                ).data,
                "readiness_assessment": StartupReadinessAssessmentSerializer(
                    submission.readiness_assessment,
                ).data,
                "action_plan": StartupReadinessActionPlanSerializer(
                    submission.action_plan,
                ).data,
                "recommendations": {
                    "generation_id": str(generation.generation_id),
                    "ranking_version": generation.ranking_version,
                    "assessment_date": generation.assessment_date.isoformat(),
                    "assessed_scheme_count": len(generation.assessments),
                    "recommendation_count": len(generation.recommendations),
                    "excluded_scheme_count": len(generation.excluded_schemes),
                    "excluded_schemes": list(generation.excluded_schemes),
                    "recommendations": recommendations,
                },
            },
            status=status.HTTP_201_CREATED,
        )
