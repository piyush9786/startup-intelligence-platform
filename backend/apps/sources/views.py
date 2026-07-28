from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import CrawlRun, Source, SourceDocument
from .serializers import CrawlRunSerializer, SourceDocumentSerializer, SourceSerializer
from .tasks import collect_source_task


class SourceViewSet(ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    filterset_fields = ["category", "state", "authority_tier", "active"]
    search_fields = ["name", "ministry", "department", "official_domain"]
    ordering_fields = ["name", "last_checked_at", "created_at"]

    def get_permissions(self):
        if self.action in {
            "create",
            "update",
            "partial_update",
            "destroy",
            "collect",
        }:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]

    @action(detail=True, methods=["post"])
    def collect(self, request, pk=None):
        source = self.get_object()
        requested_url = request.data.get("url") or None
        task = collect_source_task.delay(
            str(source.id),
            url=requested_url,
            trigger=CrawlRun.Trigger.API,
        )
        return Response(
            {
                "task_id": task.id,
                "source_id": str(source.id),
                "status": "queued",
            },
            status=202,
        )


class SourceDocumentViewSet(ReadOnlyModelViewSet):
    queryset = SourceDocument.objects.select_related("source", "crawl_run").all()
    serializer_class = SourceDocumentSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["source", "status", "mime_type", "is_current"]
    search_fields = ["title", "source_url", "final_url", "content_hash"]
    ordering_fields = ["retrieved_at", "version_number", "content_length"]


class CrawlRunViewSet(ReadOnlyModelViewSet):
    queryset = CrawlRun.objects.select_related("source").all()
    serializer_class = CrawlRunSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["source", "status", "trigger"]
    search_fields = ["source__name", "requested_url", "error_message"]
    ordering_fields = ["created_at", "started_at", "finished_at"]
