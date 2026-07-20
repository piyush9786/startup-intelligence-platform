from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from .models import Source
from .serializers import SourceSerializer


class SourceViewSet(ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    filterset_fields = ["category", "state", "authority_tier", "active"]
    search_fields = ["name", "ministry", "department", "official_domain"]
    ordering_fields = ["name", "last_checked_at", "created_at"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
