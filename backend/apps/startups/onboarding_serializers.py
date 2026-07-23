from rest_framework import serializers

from apps.startups.models import OnboardingProgress


class OnboardingProgressSerializer(
    serializers.ModelSerializer,
):
    owner_id = serializers.UUIDField(read_only=True)
    should_show = serializers.SerializerMethodField()
    total_steps = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingProgress
        fields = (
            "id",
            "owner_id",
            "tour_version",
            "variant",
            "status",
            "current_step",
            "total_steps",
            "should_show",
            "started_at",
            "dismissed_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_should_show(self, instance):
        return instance.status == OnboardingProgress.Status.ACTIVE

    def get_total_steps(self, instance):
        del instance
        return OnboardingProgress.TOTAL_STEPS


class OnboardingProgressActionSerializer(
    serializers.Serializer,
):
    action = serializers.ChoiceField(
        choices=(
            "set_step",
            "dismiss",
            "resume",
            "complete",
        ),
    )
    current_step = serializers.IntegerField(
        min_value=1,
        max_value=OnboardingProgress.TOTAL_STEPS,
        required=False,
    )

    def validate(self, attrs):
        action = attrs["action"]
        current_step = attrs.get("current_step")

        if action == "set_step" and current_step is None:
            raise serializers.ValidationError(
                {"current_step": ("A current step is required for the set_step action.")}
            )

        if action != "set_step" and current_step is not None:
            raise serializers.ValidationError(
                {"current_step": ("A current step is accepted only for the set_step action.")}
            )

        return attrs
