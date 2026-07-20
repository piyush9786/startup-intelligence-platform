from rest_framework import serializers

from .models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateEvidence,
    EligibilityRuleCandidate,
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
