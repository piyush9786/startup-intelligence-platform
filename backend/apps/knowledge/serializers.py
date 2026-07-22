from rest_framework import serializers

from .models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateEvidence,
    EligibilityRuleCandidate,
    ExternalSchemeRecord,
    KnowledgeExtractionRun,
    RequiredDocumentCandidate,
    SchemeCandidate,
)


class CandidateEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvidence
        fields = "__all__"


class EligibilityRuleCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityRuleCandidate
        fields = "__all__"


class BenefitCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitCandidate
        fields = "__all__"


class RequiredDocumentCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredDocumentCandidate
        fields = "__all__"


class ApplicationStepCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStepCandidate
        fields = "__all__"


class KnowledgeExtractionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeExtractionRun
        fields = "__all__"


class SchemeCandidateSerializer(serializers.ModelSerializer):
    evidence = CandidateEvidenceSerializer(many=True, read_only=True)
    eligibility_rules = EligibilityRuleCandidateSerializer(
        many=True,
        read_only=True,
    )
    benefit_items = BenefitCandidateSerializer(many=True, read_only=True)
    required_document_items = RequiredDocumentCandidateSerializer(
        many=True,
        read_only=True,
    )
    application_steps = ApplicationStepCandidateSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SchemeCandidate
        fields = "__all__"

class ExternalSchemeRecordSerializer(serializers.ModelSerializer):
    dataset_key = serializers.CharField(
        source="dataset.dataset_key",
        read_only=True,
    )
    dataset_name = serializers.CharField(
        source="dataset.dataset_name",
        read_only=True,
    )
    source_type = serializers.SerializerMethodField()
    verification_label = serializers.SerializerMethodField()
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = ExternalSchemeRecord
        fields = (
            "id",
            "external_id",
            "scheme_name",
            "normalized_name",
            "ministry",
            "department",
            "sector",
            "startup_stage",
            "startup_type",
            "industry",
            "central_state",
            "state",
            "funding_type",
            "funding_amount",
            "financial_instrument",
            "eligibility",
            "women_eligible",
            "sc_st_eligible",
            "dpiit_required",
            "startup_age_limit",
            "revenue_criteria",
            "tax_benefits",
            "documents_required",
            "application_process",
            "official_website_label",
            "official_application_url",
            "source_portal",
            "claimed_last_updated",
            "quality_warnings",
            "review_status",
            "matched_scheme_id",
            "dataset_key",
            "dataset_name",
            "source_type",
            "verification_label",
            "disclaimer",
            "updated_at",
        )
        read_only_fields = fields

    def get_source_type(self, obj) -> str:
        return "external"

    def get_verification_label(self, obj) -> str:
        if obj.review_status == ExternalSchemeRecord.ReviewStatus.VERIFIED:
            return "Verified"

        return "Needs review"

    def get_disclaimer(self, obj) -> str:
        return (
            "Information supplied by an external dataset. "
            "Verify details on the official source before applying."
        )
