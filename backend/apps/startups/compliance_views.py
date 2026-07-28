from __future__ import annotations

from datetime import timedelta

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from .workspace_models import ComplianceRecord
from .workspace_serializers import ComplianceRecordSerializer
from .workspace_views import ComplianceRecordViewSet as BaseComplianceRecordViewSet


class ComplianceTrackingSerializer(ComplianceRecordSerializer):
    """Expose the dates and state founders need to act on renewals."""

    reminder_starts_on = serializers.SerializerMethodField()
    renewal_due = serializers.SerializerMethodField()

    class Meta(ComplianceRecordSerializer.Meta):
        fields = ComplianceRecordSerializer.Meta.fields + (
            "reminder_starts_on",
            "renewal_due",
        )
        read_only_fields = ComplianceRecordSerializer.Meta.read_only_fields + (
            "reminder_starts_on",
            "renewal_due",
        )

    def get_reminder_starts_on(self, obj):
        if obj.expires_on is None:
            return None
        return obj.expires_on - timedelta(days=obj.renewal_reminder_days)

    def get_renewal_due(self, obj):
        days_remaining = obj.days_until_expiry
        return bool(
            days_remaining is not None
            and 0 <= days_remaining <= obj.renewal_reminder_days
            and obj.effective_status
            in {
                ComplianceRecord.Status.ACTIVE,
                ComplianceRecord.Status.IN_PROGRESS,
            }
        )

    def validate_renewal_reminder_days(self, value):
        if not 1 <= value <= 365:
            raise serializers.ValidationError(
                "Renewal reminders must be between 1 and 365 days."
            )
        return value


class ComplianceRecordViewSet(BaseComplianceRecordViewSet):
    """Founder-owned compliance CRUD with effective expiry summaries."""

    serializer_class = ComplianceTrackingSerializer

    @action(detail=False, methods=["get"])
    def summary(self, request):
        records = list(self.filter_queryset(self.get_queryset()))
        summary = {
            "total": len(records),
            "active": 0,
            "expired": 0,
            "expiring_within_30_days": 0,
            "renewal_due": 0,
            "in_progress": 0,
        }

        for record in records:
            effective_status = record.effective_status
            days_remaining = record.days_until_expiry

            if effective_status == ComplianceRecord.Status.ACTIVE:
                summary["active"] += 1
            elif effective_status == ComplianceRecord.Status.EXPIRED:
                summary["expired"] += 1
            elif effective_status == ComplianceRecord.Status.IN_PROGRESS:
                summary["in_progress"] += 1

            is_renewable_status = effective_status in {
                ComplianceRecord.Status.ACTIVE,
                ComplianceRecord.Status.IN_PROGRESS,
            }
            if (
                is_renewable_status
                and days_remaining is not None
                and 0 <= days_remaining <= 30
            ):
                summary["expiring_within_30_days"] += 1

            if (
                is_renewable_status
                and days_remaining is not None
                and 0 <= days_remaining <= record.renewal_reminder_days
            ):
                summary["renewal_due"] += 1

        return Response(summary)
