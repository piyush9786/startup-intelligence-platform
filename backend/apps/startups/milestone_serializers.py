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
    dependencies = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=StartupMilestone.objects.none(),
    )
    dependencies_detail = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        profile = self.context.get("startup_profile")

        if request is not None and profile is not None:
            self.fields["dependencies"].queryset = (
                StartupMilestone.objects.filter(
                    owner=request.user,
                    startup_profile=profile,
                )
            )

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
            "status",
            "status_display",
            "dependencies_detail",
            "completion_evidence",
            "updates_log",
            "completed_at",
            "plan_version",
            "created_at",
            "updated_at",
        )

    def validate_dependencies(self, dependencies):
        request = self.context.get("request")
        profile = self.context.get("startup_profile")

        if request is None or profile is None:
            raise serializers.ValidationError(
                "Milestone dependency scope could not be established."
            )

        instance_id = self.instance.pk if self.instance is not None else None

        for dependency in dependencies:
            if dependency.owner_id != request.user.id:
                raise serializers.ValidationError(
                    "Every dependency must belong to the authenticated founder."
                )

            if dependency.startup_profile_id != profile.id:
                raise serializers.ValidationError(
                    "Every dependency must belong to the current startup profile."
                )

            if instance_id is not None and dependency.pk == instance_id:
                raise serializers.ValidationError(
                    "A milestone cannot depend on itself."
                )

        return dependencies

    def get_dependencies_detail(self, obj):
        return [
            {
                "id": str(dependency.id),
                "title": dependency.title,
                "status": dependency.status,
                "status_display": dependency.get_status_display(),
            }
            for dependency in obj.dependencies.all()
        ]


class StartupMilestoneCompleteSerializer(serializers.Serializer):
    evidence = serializers.JSONField(required=False, default=dict)


class StartupMilestoneLogUpdateSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000)
