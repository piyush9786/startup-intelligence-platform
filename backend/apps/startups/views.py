from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import StartupProfile
from .serializers import StartupProfileSerializer


class StartupProfileViewSet(ModelViewSet):
    serializer_class = StartupProfileSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["startup_name", "description", "state"]
    filterset_fields = ["stage", "state", "dpiit_recognized", "udyam_registered"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StartupProfile.objects.all()
        return StartupProfile.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
