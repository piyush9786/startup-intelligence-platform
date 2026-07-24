"""
Serializers for the Execution & Milestones Engine endpoints.
"""
from rest_framework import serializers

from .models import StartupMilestone


class StartupMilestoneSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    dependencies_detail = serializers.SerializerMethodField()

    class Meta:
        model = StartupMilestone
        fields = (
            "id",
            "title",
            "description",
            "category",
            "category_display",
            "status",
            "status_display",
            "target_date",
            "dependencies",
            "dependencies_detail",
            "linked_scheme_id",
            "linked_builder_section",
            "completion_evidence",
            "updates_log",
            "completed_at",
            "plan_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_display",
            "status_display",
            "dependencies_detail",
            "completed_at",
            "plan_version",
            "created_at",
            "updated_at",
        )

    def get_dependencies_detail(self, obj):
        return [
            {
                "id": str(dep.id),
                "title": dep.title,
                "status": dep.status,
                "status_display": dep.get_status_display(),
            }
            for dep in obj.dependencies.all()
        ]


class StartupMilestoneCompleteSerializer(serializers.Serializer):
    evidence = serializers.JSONField(required=False, default=dict)
    force = serializers.BooleanField(default=False)


class StartupMilestoneLogUpdateSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000)
