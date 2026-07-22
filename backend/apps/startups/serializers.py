from django.utils import timezone
from rest_framework import serializers

from .assessment_schema import assessment_completion_percent
from .models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupAssessmentDraft,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from .services.assessment_drafts import (
    get_or_create_startup_assessment_draft,
)


class StartupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupProfile
        fields = "__all__"
        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
        )


class StartupAssessmentDraftSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(read_only=True)
    startup_profile_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    completion_percent = serializers.SerializerMethodField()

    class Meta:
        model = StartupAssessmentDraft
        fields = (
            "id",
            "owner_id",
            "startup_profile_id",
            "status",
            "current_step",
            "data",
            "completion_percent",
            "submitted_at",
            "submitted_profile_snapshot",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_completion_percent(self, instance):
        return assessment_completion_percent(instance.data)


class StartupAssessmentDraftCreateSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    current_step = serializers.IntegerField(
        min_value=1,
        max_value=8,
        default=1,
    )
    data = serializers.JSONField(
        required=False,
        default=dict,
    )

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Assessment draft data must be a JSON object.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        startup_profile_id = attrs.get("startup_profile_id")
        startup_profile = None

        if startup_profile_id is not None:
            startup_profile = (
                StartupProfile.objects.filter(
                    pk=startup_profile_id,
                    owner=request.user,
                )
                .select_related("owner")
                .first()
            )
            if startup_profile is None:
                raise serializers.ValidationError(
                    {"startup_profile_id": ("The startup profile was not found for this user.")}
                )

        attrs["startup_profile"] = startup_profile
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        startup_profile = validated_data.pop("startup_profile")
        validated_data.pop("startup_profile_id", None)
        supplied_data = validated_data.pop("data", {})
        current_step = validated_data.pop("current_step", 1)

        draft, created = get_or_create_startup_assessment_draft(
            owner=request.user,
            startup_profile=startup_profile,
            current_step=current_step,
            supplied_data=supplied_data,
        )
        self.created = created
        return draft


class StartupAssessmentDraftUpdateSerializer(serializers.Serializer):
    current_step = serializers.IntegerField(
        min_value=1,
        max_value=8,
        required=False,
    )
    data = serializers.JSONField(required=False)

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Assessment draft data must be a JSON object.")
        return value

    def update(self, instance, validated_data):
        if instance.status != StartupAssessmentDraft.Status.DRAFT:
            raise serializers.ValidationError("Submitted assessment drafts cannot be changed.")

        if "current_step" in validated_data:
            instance.current_step = validated_data["current_step"]
        if "data" in validated_data:
            instance.data = {
                **instance.data,
                **validated_data["data"],
            }
        instance.save()
        return instance


class StartupAssessmentDraftSubmitRequestSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(
        required=False,
        default=True,
    )

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Submission confirmation is required.")
        return value


class StartupAssessmentSubmissionSerializer(serializers.Serializer):
    startup_name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    incorporation_type = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    incorporation_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    district = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    stage = serializers.ChoiceField(
        choices=StartupProfile.Stage.choices,
    )
    sectors = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    technologies = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    founder_categories = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    founder_gender = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )
    dpiit_recognized = serializers.BooleanField(
        required=False,
        allow_null=True,
    )
    udyam_registered = serializers.BooleanField(
        required=False,
        allow_null=True,
    )
    annual_turnover = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    revenue_stage = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    funding_required = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    funding_purpose = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    team_size = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )

    founder_role = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    founder_experience_years = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    founder_education = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    number_of_founders = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )
    business_model = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    customer_status = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    target_customer = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    traction_summary = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    monthly_revenue = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    funding_stage = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    capital_raised = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    runway_months = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    preferred_funding_type = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    team_roles = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    skills_needs = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    incubator_affiliation = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    mentor_access = serializers.BooleanField(
        required=False,
        allow_null=True,
    )
    cloud_credits = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    certification_needs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        allow_empty=True,
    )
    compliance_support_needs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        allow_empty=True,
    )
    resource_needs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        allow_empty=True,
    )
    entity_types = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    regulatory_registrations = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    contact_email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )
    website = serializers.URLField(
        required=False,
        allow_blank=True,
    )


class StartupReadinessEvaluationRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    assessment_date = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )
    profile = serializers.JSONField(
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        if "profile" in attrs:
            raise serializers.ValidationError(
                {"profile": ("Raw profile data is not accepted. Use startup_profile_id.")}
            )
        return attrs


class StartupReadinessRetrievalRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()


class StartupReadinessAssessmentSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupReadinessAssessment
        fields = (
            "id",
            "startup_profile_id",
            "requested_by_id",
            "assessment_date",
            "profile_snapshot",
            "status",
            "score",
            "critical_score",
            "recommended_score",
            "findings",
            "blocking_findings",
            "summary",
            "engine_version",
            "created_at",
        )
        read_only_fields = fields


class StartupReadinessActionPlanGenerationRequestSerializer(serializers.Serializer):
    readiness_assessment_id = serializers.UUIDField()
    findings = serializers.JSONField(required=False, write_only=True)
    profile = serializers.JSONField(required=False, write_only=True)
    assessment = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        raw_fields = [name for name in ("findings", "profile", "assessment") if name in attrs]
        if raw_fields:
            raise serializers.ValidationError(
                {
                    name: ("Raw readiness data is not accepted. Use readiness_assessment_id.")
                    for name in raw_fields
                }
            )
        return attrs


class StartupReadinessActionPlanSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    source_assessment_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupReadinessActionPlan
        fields = (
            "id",
            "startup_profile_id",
            "source_assessment_id",
            "requested_by_id",
            "source_assessment_snapshot",
            "readiness_status",
            "has_actions",
            "blocker_count",
            "recommendation_count",
            "total_action_count",
            "next_action",
            "items",
            "source_engine_version",
            "planner_version",
            "created_at",
        )
        read_only_fields = fields


class StartupAdvisorSnapshotGenerationRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    profile = serializers.JSONField(required=False, write_only=True)
    readiness = serializers.JSONField(required=False, write_only=True)
    assessment = serializers.JSONField(required=False, write_only=True)
    action_plan = serializers.JSONField(required=False, write_only=True)
    recommendations = serializers.JSONField(
        required=False,
        write_only=True,
    )
    generation = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        raw_fields = [
            name
            for name in (
                "profile",
                "readiness",
                "assessment",
                "action_plan",
                "recommendations",
                "generation",
            )
            if name in attrs
        ]
        if raw_fields:
            raise serializers.ValidationError(
                {
                    name: ("Raw advisor data is not accepted. Use startup_profile_id.")
                    for name in raw_fields
                }
            )
        return attrs


class StartupAdvisorSnapshotSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    readiness_assessment_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    readiness_action_plan_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    recommendation_generation_run_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupAdvisorSnapshot
        fields = (
            "id",
            "startup_profile_id",
            "requested_by_id",
            "readiness_assessment_id",
            "readiness_action_plan_id",
            "recommendation_generation_run_id",
            "has_readiness_assessment",
            "has_action_plan",
            "has_recommendation_generation",
            "profile_snapshot",
            "readiness_snapshot",
            "action_plan_snapshot",
            "recommendation_generation_snapshot",
            "recommendations_snapshot",
            "recommendation_count",
            "snapshot_version",
            "created_at",
        )
        read_only_fields = fields


class StartupAdvisorBriefingGenerationRequestSerializer(serializers.Serializer):
    advisor_snapshot_id = serializers.UUIDField()
    snapshot = serializers.JSONField(required=False, write_only=True)
    prompt = serializers.CharField(required=False, write_only=True)
    model = serializers.CharField(required=False, write_only=True)
    provider = serializers.CharField(required=False, write_only=True)
    briefing = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        unsupported = [
            name
            for name in (
                "snapshot",
                "prompt",
                "model",
                "provider",
                "briefing",
            )
            if name in attrs
        ]
        if unsupported:
            raise serializers.ValidationError(
                {
                    name: ("This value is server-controlled. Use advisor_snapshot_id only.")
                    for name in unsupported
                }
            )
        return attrs


class StartupAdvisorBriefingSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    source_snapshot_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupAdvisorBriefing
        fields = (
            "id",
            "startup_profile_id",
            "source_snapshot_id",
            "requested_by_id",
            "provider",
            "model_name",
            "prompt_version",
            "schema_version",
            "generation_parameters",
            "prompt_snapshot",
            "briefing",
            "prompt_token_count",
            "output_token_count",
            "total_duration_ns",
            "response_metadata",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields


class StartupAdvisorBriefingJobSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    source_snapshot_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    briefing_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    is_terminal = serializers.SerializerMethodField()

    class Meta:
        model = StartupAdvisorBriefingJob
        fields = (
            "id",
            "startup_profile_id",
            "source_snapshot_id",
            "requested_by_id",
            "briefing_id",
            "status",
            "error_code",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "is_terminal",
        )
        read_only_fields = fields

    def get_is_terminal(self, obj):
        return obj.status in (
            StartupAdvisorBriefingJob.Status.SUCCEEDED,
            StartupAdvisorBriefingJob.Status.FAILED,
        )
