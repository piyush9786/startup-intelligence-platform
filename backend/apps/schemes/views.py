from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from .models import Scheme, SchemeVersion
from .serializers import SchemeSerializer


class SchemeViewSet(ModelViewSet):
    queryset = Scheme.objects.select_related("authority", "current_version").all()
    serializer_class = SchemeSerializer
    filterset_fields = ["lifecycle_status", "authority"]
    search_fields = ["canonical_name", "short_name", "authority__name"]
    ordering_fields = ["canonical_name", "created_at", "updated_at"]

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return queryset
        return queryset.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=(
                SchemeVersion.VerificationStatus.VERIFIED
            ),
        )

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
