from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.startups.models import StartupProfile

from .models import Scheme, SchemeVersion
from .serializers import SchemeSerializer
from .services.hybrid_search import (
    HybridSearchConfigurationError,
    hybrid_search_verified_schemes,
)


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



    @action(
        detail=False,
        methods=["get"],
        url_path="hybrid-search",
    )
    def hybrid_search(self, request):
        query = str(request.query_params.get("q", "")).strip()
        if not query:
            raise ValidationError({"q": "A search query is required."})
        if len(query) > 500:
            raise ValidationError({"q": "The search query cannot exceed 500 characters."})

        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"limit": "Limit must be an integer."}) from exc
        if limit < 1 or limit > 50:
            raise ValidationError({"limit": "Limit must be between 1 and 50."})

        startup_profile = None
        profile_id = request.query_params.get("startup_profile_id")
        if profile_id:
            if not request.user.is_authenticated:
                raise NotAuthenticated(
                    "Authentication is required to apply a startup profile to scheme search."
                )
            profiles = StartupProfile.objects.all()
            if not (request.user.is_staff or request.user.is_superuser):
                profiles = profiles.filter(owner=request.user)
            try:
                startup_profile = profiles.get(pk=profile_id)
            except (StartupProfile.DoesNotExist, ValueError) as exc:
                raise PermissionDenied(
                    "The requested startup profile is not available to this account."
                ) from exc

        try:
            payload = hybrid_search_verified_schemes(
                query=query,
                startup_profile=startup_profile,
                limit=limit,
            )
        except HybridSearchConfigurationError as exc:
            raise ValidationError(
                {
                    "detail": str(exc),
                    "code": "hybrid_search_model_invalid",
                }
            ) from exc

        return Response(payload)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
