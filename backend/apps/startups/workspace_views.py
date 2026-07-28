from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.models import User
from apps.recommendations.models import SchemeApplicationTracker
from apps.sources.services.storage import delete_object, stream_object

from .workspace_models import (
    ApplicationStageEvent,
    ApplicationTask,
    ComplianceRecord,
    ConsultantProfile,
    FounderVaultDocument,
)
from .workspace_serializers import (
    ApplicationStageEventSerializer,
    ApplicationTaskSerializer,
    ComplianceRecordSerializer,
    ConsultantProfileSerializer,
    FounderVaultDocumentSerializer,
)


class ComplianceRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ComplianceRecordSerializer
    queryset = ComplianceRecord.objects.none()
    filterset_fields = (
        "startup_profile",
        "compliance_type",
        "status",
    )
    ordering_fields = (
        "expires_on",
        "title",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "registration_number",
        "issuing_authority",
        "notes",
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return ComplianceRecord.objects.filter(
            owner=self.request.user,
        ).select_related("startup_profile")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        records = self.get_queryset()
        today = timezone.localdate()
        horizon = today + timedelta(days=30)
        return Response(
            {
                "total": records.count(),
                "active": records.filter(
                    status=ComplianceRecord.Status.ACTIVE,
                ).count(),
                "expired": records.filter(
                    Q(status=ComplianceRecord.Status.EXPIRED)
                    | Q(expires_on__lt=today)
                ).count(),
                "expiring_within_30_days": records.filter(
                    expires_on__gte=today,
                    expires_on__lte=horizon,
                ).count(),
                "in_progress": records.filter(
                    status=ComplianceRecord.Status.IN_PROGRESS,
                ).count(),
            }
        )


class FounderVaultDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FounderVaultDocumentSerializer
    queryset = FounderVaultDocument.objects.none()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = (
        "startup_profile",
        "category",
        "is_archived",
    )
    ordering_fields = (
        "created_at",
        "updated_at",
        "expires_on",
        "title",
    )
    search_fields = (
        "title",
        "original_filename",
        "tags",
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return FounderVaultDocument.objects.filter(
            owner=self.request.user,
        ).select_related("startup_profile")

    def perform_destroy(self, instance):
        storage_key = instance.storage_key
        bucket_name = instance.bucket_name
        super().perform_destroy(instance)
        delete_object(storage_key, bucket_name=bucket_name)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        response = StreamingHttpResponse(
            stream_object(
                document.storage_key,
                bucket_name=document.bucket_name,
            ),
            content_type=document.mime_type or "application/octet-stream",
        )
        safe_name = document.original_filename.replace('"', "")
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_name}"'
        )
        response["Content-Length"] = str(document.size_bytes)
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ConsultantProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConsultantProfileSerializer
    queryset = ConsultantProfile.objects.none()
    filterset_fields = (
        "availability",
        "verification_status",
        "is_public",
    )
    ordering_fields = (
        "years_experience",
        "average_rating",
        "hourly_rate",
        "updated_at",
    )
    search_fields = (
        "headline",
        "bio",
        "expertise",
        "languages",
        "states_served",
        "industries",
        "user__first_name",
        "user__last_name",
        "user__username",
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return (
            ConsultantProfile.objects.select_related("user")
            .filter(Q(is_public=True) | Q(user=self.request.user))
            .distinct()
        )

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in {User.Role.CONSULTANT, User.Role.ADMIN}:
            raise serializers.ValidationError(
                "Only consultant accounts can create a marketplace profile."
            )
        if ConsultantProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                "A consultant profile already exists for this account."
            )
        serializer.save(user=user)

    def perform_update(self, serializer):
        if serializer.instance.user_id != self.request.user.id:
            raise PermissionDenied(
                "You may update only your own consultant profile."
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id:
            raise PermissionDenied(
                "You may delete only your own consultant profile."
            )
        instance.delete()


class ApplicationTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ApplicationTaskSerializer
    queryset = ApplicationTask.objects.none()
    filterset_fields = (
        "application",
        "status",
        "due_on",
    )
    ordering_fields = (
        "sort_order",
        "due_on",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "notes",
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return ApplicationTask.objects.filter(
            application__owner=self.request.user,
        ).select_related(
            "application",
            "application__startup_profile",
            "application__scheme_version__scheme",
        )


class ApplicationStageEventViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ApplicationStageEventSerializer
    queryset = ApplicationStageEvent.objects.none()
    filterset_fields = (
        "application",
        "to_stage",
    )
    ordering_fields = (
        "occurred_at",
        "created_at",
    )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return ApplicationStageEvent.objects.filter(
            application__owner=self.request.user,
        ).select_related("application", "created_by")


class ApplicationWorkflowSerializer(serializers.ModelSerializer):
    scheme_name = serializers.SerializerMethodField()
    tasks = ApplicationTaskSerializer(
        source="workflow_tasks",
        many=True,
        read_only=True,
    )
    events = ApplicationStageEventSerializer(
        source="stage_events",
        many=True,
        read_only=True,
    )

    class Meta:
        model = SchemeApplicationTracker
        fields = (
            "id",
            "startup_profile",
            "scheme_version",
            "scheme_name",
            "stage",
            "submission_reference",
            "notes",
            "submitted_at",
            "application_data",
            "tasks",
            "events",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_scheme_name(self, obj):
        return obj.scheme_version.scheme.canonical_name


class ApplicationWorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ApplicationWorkflowSerializer
    queryset = SchemeApplicationTracker.objects.none()

    ALLOWED_TRANSITIONS = {
        SchemeApplicationTracker.Stage.DRAFT: {
            SchemeApplicationTracker.Stage.SUBMITTED,
        },
        SchemeApplicationTracker.Stage.SUBMITTED: {
            SchemeApplicationTracker.Stage.UNDER_REVIEW,
            SchemeApplicationTracker.Stage.REJECTED,
        },
        SchemeApplicationTracker.Stage.UNDER_REVIEW: {
            SchemeApplicationTracker.Stage.APPROVED,
            SchemeApplicationTracker.Stage.REJECTED,
        },
        SchemeApplicationTracker.Stage.REJECTED: {
            SchemeApplicationTracker.Stage.DRAFT,
        },
        SchemeApplicationTracker.Stage.APPROVED: set(),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return (
            SchemeApplicationTracker.objects.filter(
                owner=self.request.user,
            )
            .select_related(
                "startup_profile",
                "scheme_version__scheme",
            )
            .prefetch_related(
                "workflow_tasks",
                "stage_events__created_by",
            )
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        target_stage = str(request.data.get("stage") or "").strip()
        note = str(request.data.get("note") or "").strip()

        valid_stages = {
            choice for choice, _ in SchemeApplicationTracker.Stage.choices
        }
        if target_stage not in valid_stages:
            raise serializers.ValidationError(
                {"stage": "Select a valid application stage."}
            )

        with transaction.atomic():
            application = (
                SchemeApplicationTracker.objects.select_for_update()
                .filter(owner=request.user, pk=pk)
                .select_related("scheme_version__scheme", "startup_profile")
                .first()
            )
            if application is None:
                raise NotFound("Application was not found.")

            previous_stage = application.stage
            allowed = self.ALLOWED_TRANSITIONS.get(previous_stage, set())
            if target_stage not in allowed:
                raise serializers.ValidationError(
                    {
                        "stage": (
                            f"The application cannot move from "
                            f"{previous_stage} to {target_stage}."
                        )
                    }
                )

            application.stage = target_stage
            update_fields = ["stage", "updated_at"]
            if target_stage == SchemeApplicationTracker.Stage.SUBMITTED:
                application.submitted_at = timezone.now()
                update_fields.append("submitted_at")
            application.save(update_fields=update_fields)

            ApplicationStageEvent.objects.create(
                application=application,
                from_stage=previous_stage,
                to_stage=target_stage,
                note=note,
                created_by=request.user,
            )

        refreshed = self.get_queryset().get(pk=application.pk)
        return Response(
            self.get_serializer(refreshed).data,
            status=status.HTTP_200_OK,
        )
