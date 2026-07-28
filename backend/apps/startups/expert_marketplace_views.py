from __future__ import annotations

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User

from .expert_marketplace_models import ConsultationRequest
from .expert_marketplace_serializers import (
    ConsultationRequestSerializer,
    ConsultationResponseSerializer,
)
from .workspace_models import ConsultantProfile


class ConsultationRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConsultationRequestSerializer
    queryset = ConsultationRequest.objects.none()
    filterset_fields = (
        "startup_profile",
        "consultant",
        "status",
        "preferred_date",
    )
    ordering_fields = (
        "created_at",
        "updated_at",
        "preferred_date",
        "scheduled_for",
        "status",
    )
    search_fields = (
        "topic",
        "message",
        "consultant_response",
        "startup_profile__startup_name",
        "consultant__user__first_name",
        "consultant__user__last_name",
        "consultant__user__username",
    )

    CONSULTANT_TRANSITIONS = {
        ConsultationRequest.Status.REQUESTED: {
            ConsultationRequest.Status.ACCEPTED,
            ConsultationRequest.Status.DECLINED,
        },
        ConsultationRequest.Status.ACCEPTED: {
            ConsultationRequest.Status.SCHEDULED,
            ConsultationRequest.Status.DECLINED,
        },
        ConsultationRequest.Status.SCHEDULED: {
            ConsultationRequest.Status.COMPLETED,
        },
        ConsultationRequest.Status.DECLINED: set(),
        ConsultationRequest.Status.COMPLETED: set(),
        ConsultationRequest.Status.CANCELLED: set(),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        if self.request.user.is_staff or self.request.user.role == User.Role.ADMIN:
            ownership = Q()
        else:
            ownership = Q(founder=self.request.user) | Q(
                consultant__user=self.request.user
            )
        return (
            ConsultationRequest.objects.filter(ownership)
            .select_related(
                "founder",
                "startup_profile",
                "consultant__user",
            )
            .distinct()
        )

    def perform_create(self, serializer):
        if self.request.user.role not in {User.Role.FOUNDER, User.Role.ADMIN}:
            raise PermissionDenied(
                "Only founder accounts can request a consultation."
            )
        serializer.save()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            consultation = (
                ConsultationRequest.objects.select_for_update()
                .filter(founder=request.user, pk=pk)
                .select_related("founder", "startup_profile", "consultant__user")
                .first()
            )
            if consultation is None:
                raise NotFound("Consultation request was not found.")
            if consultation.status not in {
                ConsultationRequest.Status.REQUESTED,
                ConsultationRequest.Status.ACCEPTED,
                ConsultationRequest.Status.SCHEDULED,
            }:
                raise serializers.ValidationError(
                    {"status": "This consultation can no longer be cancelled."}
                )
            consultation.status = ConsultationRequest.Status.CANCELLED
            consultation.save(update_fields=["status", "updated_at"])

        return Response(
            self.get_serializer(consultation).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        response_serializer = ConsultationResponseSerializer(data=request.data)
        response_serializer.is_valid(raise_exception=True)
        payload = response_serializer.validated_data

        with transaction.atomic():
            consultation = (
                ConsultationRequest.objects.select_for_update()
                .filter(consultant__user=request.user, pk=pk)
                .select_related("founder", "startup_profile", "consultant__user")
                .first()
            )
            if consultation is None:
                raise NotFound("Consultation request was not found.")

            target_status = payload["status"]
            allowed = self.CONSULTANT_TRANSITIONS.get(
                consultation.status,
                set(),
            )
            if target_status not in allowed:
                raise serializers.ValidationError(
                    {
                        "status": (
                            f"The consultation cannot move from "
                            f"{consultation.status} to {target_status}."
                        )
                    }
                )

            scheduled_for = payload.get("scheduled_for")
            if (
                target_status == ConsultationRequest.Status.SCHEDULED
                and scheduled_for <= timezone.now()
            ):
                raise serializers.ValidationError(
                    {"scheduled_for": "Schedule the consultation in the future."}
                )

            consultation.status = target_status
            consultation.consultant_response = str(
                payload.get("consultant_response") or ""
            ).strip()
            if target_status == ConsultationRequest.Status.SCHEDULED:
                consultation.scheduled_for = scheduled_for
            elif target_status in {
                ConsultationRequest.Status.DECLINED,
                ConsultationRequest.Status.COMPLETED,
            }:
                consultation.scheduled_for = (
                    consultation.scheduled_for
                    if target_status == ConsultationRequest.Status.COMPLETED
                    else None
                )
            consultation.save(
                update_fields=[
                    "status",
                    "consultant_response",
                    "scheduled_for",
                    "updated_at",
                ]
            )

            if target_status == ConsultationRequest.Status.COMPLETED:
                ConsultantProfile.objects.filter(
                    pk=consultation.consultant_id
                ).update(sessions_completed=F("sessions_completed") + 1)

        return Response(
            self.get_serializer(consultation).data,
            status=status.HTTP_200_OK,
        )
