from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import CrawlFrontierEntry, DiscoveredURL, DocumentQualityAssessment
from .serializers import (
    CrawlFrontierEntrySerializer,
    CrawlFrontierRequestSerializer,
    DiscoveredURLSerializer,
    DocumentQualityAssessmentSerializer,
)
from .tasks import process_frontier_entry_task


class DiscoveredURLViewSet(ReadOnlyModelViewSet):
    queryset = DiscoveredURL.objects.select_related(
        "source",
        "parent_document",
        "last_collected_document",
    ).all()
    serializer_class = DiscoveredURLSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["source", "page_type", "status", "allowed", "crawl_depth"]
    search_fields = ["normalized_url", "anchor_text", "rejection_reason"]
    ordering_fields = ["priority", "crawl_depth", "created_at", "last_seen_at"]


class CrawlFrontierEntryViewSet(ReadOnlyModelViewSet):
    queryset = CrawlFrontierEntry.objects.select_related(
        "discovered_url",
        "discovered_url__source",
    ).all()
    serializer_class = CrawlFrontierEntrySerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["status", "discovered_url__source"]
    search_fields = ["discovered_url__normalized_url", "error_message"]
    ordering_fields = ["scheduled_at", "retry_count", "created_at"]


class DocumentQualityAssessmentViewSet(ReadOnlyModelViewSet):
    queryset = DocumentQualityAssessment.objects.select_related(
        "extraction",
        "extraction__source_document",
        "extraction__source_document__source",
    ).all()
    serializer_class = DocumentQualityAssessmentSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = [
        "page_type",
        "usable_for_discovery",
        "usable_for_rag",
        "usable_for_structured_extraction",
    ]
    search_fields = [
        "extraction__detected_title",
        "extraction__source_document__source_url",
        "rejection_reason",
    ]
    ordering_fields = ["score", "assessed_at", "created_at"]


class CrawlFrontierView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CrawlFrontierRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entries = CrawlFrontierEntry.objects.filter(
            status=CrawlFrontierEntry.Status.PENDING,
            scheduled_at__lte=timezone.now(),
        ).order_by(
            "discovered_url__priority",
            "scheduled_at",
        )[: serializer.validated_data["limit"]]
        task_ids = []
        for entry in entries:
            task = process_frontier_entry_task.delay(str(entry.id))
            entry.task_id = task.id
            entry.save(update_fields=["task_id", "updated_at"])
            task_ids.append(task.id)
        return Response(
            {"queued": len(task_ids), "task_ids": task_ids},
            status=202,
        )
