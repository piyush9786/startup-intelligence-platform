from rest_framework import serializers

from .models import Source, SourceDocument


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class SourceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceDocument
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
