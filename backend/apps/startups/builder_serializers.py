"""
Serializers for the AI Startup Builder section endpoints.
"""
from rest_framework import serializers

from .models import StartupBuilderSection


class StartupBuilderSectionSerializer(serializers.ModelSerializer):
    """Read serializer — includes AI draft and confirmed content."""

    section_type_display = serializers.CharField(
        source="get_section_type_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = StartupBuilderSection
        fields = (
            "id",
            "section_type",
            "section_type_display",
            "status",
            "status_display",
            "content",
            "ai_draft",
            "plan_version",
            "confirmed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StartupBuilderSectionUpdateSerializer(serializers.Serializer):
    """Write serializer — founder saves or confirms content."""

    content = serializers.JSONField()
    confirm = serializers.BooleanField(default=False)


PHASE_54_SECTION_TYPES = [
    StartupBuilderSection.SectionType.PROBLEM,
    StartupBuilderSection.SectionType.CUSTOMER,
    StartupBuilderSection.SectionType.INTERVIEWS,
    StartupBuilderSection.SectionType.VALIDATION,
    StartupBuilderSection.SectionType.BUSINESS_MODEL,
    StartupBuilderSection.SectionType.PRICING,
]
