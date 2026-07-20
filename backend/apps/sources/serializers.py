from rest_framework import serializers

from .models import CrawlRun, Source, SourceDocument


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "last_checked_at")


class SourceDocumentSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = SourceDocument
        fields = "__all__"
        read_only_fields = tuple(field.name for field in SourceDocument._meta.fields)


class CrawlRunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = CrawlRun
        fields = "__all__"
        read_only_fields = tuple(field.name for field in CrawlRun._meta.fields)
