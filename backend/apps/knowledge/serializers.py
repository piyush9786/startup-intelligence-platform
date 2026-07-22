from rest_framework import serializers

from .models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateEvidence,
    EligibilityRuleCandidate,
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
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


class ExternalCapitalSupportRecordSerializer(
    serializers.ModelSerializer
):
    dataset_key = serializers.CharField(
        source="dataset.dataset_key",
        read_only=True,
    )
    dataset_name = serializers.CharField(
        source="dataset.dataset_name",
        read_only=True,
    )
    source_type = serializers.SerializerMethodField()
    record_type = serializers.SerializerMethodField()
    verification_label = serializers.SerializerMethodField()
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = ExternalCapitalSupportRecord
        fields = (
            "id",
            "external_id",
            "support_name",
            "support_type",
            "scheme_name",
            "normalized_name",
            "ministry",
            "implementing_agency",
            "funding_category",
            "minimum_amount",
            "maximum_amount",
            "raw_minimum_amount",
            "raw_maximum_amount",
            "currency",
            "interest_rate_text",
            "collateral_required_text",
            "repayment_required_text",
            "startup_stage",
            "industry",
            "eligible_entity",
            "state",
            "funding_purpose",
            "claimed_scheme_status",
            "remarks",
            "quality_warnings",
            "review_status",
            "dataset_key",
            "dataset_name",
            "source_type",
            "record_type",
            "verification_label",
            "disclaimer",
            "updated_at",
        )
        read_only_fields = fields

    def get_source_type(self, obj) -> str:
        return "external"

    def get_record_type(self, obj) -> str:
        return "capital_support"

    def get_verification_label(self, obj) -> str:
        if (
            obj.review_status
            == ExternalCapitalSupportRecord
            .ReviewStatus.VERIFIED
        ):
            return "Verified"

        return "Needs review"

    def get_disclaimer(self, obj) -> str:
        return (
            "Information supplied by an external dataset. "
            "Verify funding terms with the responsible "
            "authority before applying."
        )


class ExternalCertificationRequirementRecordSerializer(
    serializers.ModelSerializer
):
    dataset_key = serializers.CharField(
        source="dataset.dataset_key",
        read_only=True,
    )
    dataset_name = serializers.CharField(
        source="dataset.dataset_name",
        read_only=True,
    )
    source_type = serializers.SerializerMethodField()
    record_type = serializers.SerializerMethodField()
    verification_label = serializers.SerializerMethodField()
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = ExternalCertificationRequirementRecord
        fields = (
            "id",
            "external_id",
            "certificate_name",
            "normalized_name",
            "certificate_type",
            "description",
            "industry",
            "startup_stage",
            "requirement_level",
            "eligibility",
            "benefits",
            "validity",
            "renewal_period",
            "issuing_authority",
            "official_document_text",
            "official_apply_url",
            "quality_warnings",
            "review_status",
            "display_eligible",
            "dataset_key",
            "dataset_name",
            "source_type",
            "record_type",
            "verification_label",
            "disclaimer",
            "updated_at",
        )
        read_only_fields = fields

    def get_source_type(self, obj) -> str:
        return "external"

    def get_record_type(self, obj) -> str:
        return "certification_requirement"

    def get_verification_label(self, obj) -> str:
        if (
            obj.review_status
            == ExternalCertificationRequirementRecord
            .ReviewStatus.VERIFIED
        ):
            return "Verified"

        return "Needs review"

    def get_disclaimer(self, obj) -> str:
        return (
            "Information supplied by an external dataset. "
            "Confirm the requirement and application process "
            "with the issuing authority."
        )
