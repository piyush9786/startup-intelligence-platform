from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.sources.models import SourceDocument

from .models import DocumentChunk, DocumentExtraction
from .serializers import (
    DocumentChunkSerializer,
    DocumentExtractionSerializer,
    ProcessDocumentRequestSerializer,
)
from .tasks import process_source_document_task


class DocumentExtractionViewSet(ReadOnlyModelViewSet):
    queryset = DocumentExtraction.objects.select_related(
        "source_document",
        "source_document__source",
    ).all()
    serializer_class = DocumentExtractionSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = [
        "status",
        "extractor_version",
        "source_document__source",
    ]
    search_fields = [
        "detected_title",
        "source_document__title",
        "source_document__source_url",
        "text_hash",
        "error_message",
    ]
    ordering_fields = [
        "created_at",
        "finished_at",
        "word_count",
        "chunk_count",
    ]


class DocumentChunkViewSet(ReadOnlyModelViewSet):
    queryset = DocumentChunk.objects.select_related(
        "extraction",
        "extraction__source_document",
    ).all()
    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = [
        "extraction",
        "page_number",
        "extraction__source_document",
    ]
    search_fields = ["heading", "text", "text_hash"]
    ordering_fields = ["chunk_index", "created_at", "token_estimate"]


class ProcessDocumentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ProcessDocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = get_object_or_404(
            SourceDocument,
            id=serializer.validated_data["document_id"],
        )
        task = process_source_document_task.delay(
            str(document.id),
            force=serializer.validated_data["force"],
        )
        return Response(
            {
                "task_id": task.id,
                "document_id": str(document.id),
                "status": "queued",
            },
            status=202,
        )
