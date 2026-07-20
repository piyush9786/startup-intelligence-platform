from rest_framework import serializers

from .models import DocumentChunk, DocumentExtraction


class DocumentExtractionSerializer(serializers.ModelSerializer):
    source_document_title = serializers.CharField(
        source="source_document.title",
        read_only=True,
    )
    source_name = serializers.CharField(
        source="source_document.source.name",
        read_only=True,
    )

    class Meta:
        model = DocumentExtraction
        fields = "__all__"


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = "__all__"


class ProcessDocumentRequestSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    force = serializers.BooleanField(default=False)
