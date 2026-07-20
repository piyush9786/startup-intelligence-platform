from rest_framework import serializers


class EligibilityRequestSerializer(serializers.Serializer):
    scheme_id = serializers.UUIDField()
    profile = serializers.JSONField()
