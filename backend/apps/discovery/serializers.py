from rest_framework import serializers

from .models import CrawlFrontierEntry, DiscoveredURL, DocumentQualityAssessment


class DiscoveredURLSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = DiscoveredURL
        fields = "__all__"


class CrawlFrontierEntrySerializer(serializers.ModelSerializer):
    url = serializers.CharField(
        source="discovered_url.normalized_url",
        read_only=True,
    )
    source_name = serializers.CharField(
        source="discovered_url.source.name",
        read_only=True,
    )

    class Meta:
        model = CrawlFrontierEntry
        fields = "__all__"


class DocumentQualityAssessmentSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(
        source="extraction.source_document.source.name",
        read_only=True,
    )
    source_url = serializers.CharField(
        source="extraction.source_document.source_url",
        read_only=True,
    )

    class Meta:
        model = DocumentQualityAssessment
        fields = "__all__"


class CrawlFrontierRequestSerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
