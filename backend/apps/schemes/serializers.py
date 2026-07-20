from rest_framework import serializers

from .models import Authority, EligibilityRule, Scheme, SchemeVersion


class AuthoritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Authority
        fields = "__all__"


class EligibilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityRule
        fields = "__all__"


class SchemeVersionSerializer(serializers.ModelSerializer):
    eligibility_rules = EligibilityRuleSerializer(many=True, read_only=True)

    class Meta:
        model = SchemeVersion
        fields = "__all__"


class SchemeSerializer(serializers.ModelSerializer):
    authority_name = serializers.CharField(source="authority.name", read_only=True)
    current_version_detail = SchemeVersionSerializer(source="current_version", read_only=True)

    class Meta:
        model = Scheme
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
