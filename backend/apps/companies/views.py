from django.db.models import Count, Prefetch
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Company, CompanyDataSource, CompanyMetric, CompanyOutcome, RawCompanyDataset
from .serializers import (
    CompanyDataSourceSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
    RawCompanyDatasetSerializer,
)


class CompanyViewSet(ReadOnlyModelViewSet):
    filterset_fields = [
        "industry",
        "sub_industry",
        "business_model",
        "customer_segment",
        "country",
        "state",
        "founded_year",
        "operating_status",
        "verification_status",
    ]
    search_fields = ["canonical_name", "aliases__alias", "website"]
    ordering_fields = ["canonical_name", "founded_year", "created_at", "updated_at"]

    def get_queryset(self):
        queryset = Company.objects.annotate(
            provenance_count=Count("source_records", distinct=True)
        ).order_by("canonical_name", "id")
        user = self.request.user
        if not user.is_staff and not user.is_superuser:
            queryset = queryset.filter(
                verification_status__in=[
                    Company.VerificationStatus.PARTIALLY_VERIFIED,
                    Company.VerificationStatus.VERIFIED,
                ],
                source_records__source__active=True,
                source_records__source__verification_status__in=[
                    CompanyDataSource.VerificationStatus.REVIEWED,
                    CompanyDataSource.VerificationStatus.VERIFIED,
                ],
            ).distinct()
        if self.action == "retrieve":
            return queryset.prefetch_related(
                "aliases",
                Prefetch(
                    "metrics",
                    queryset=CompanyMetric.objects.select_related("source"),
                ),
                Prefetch(
                    "outcomes",
                    queryset=CompanyOutcome.objects.select_related("source"),
                ),
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CompanyDetailSerializer
        return CompanyListSerializer


class CompanyDataSourceViewSet(ModelViewSet):
    queryset = CompanyDataSource.objects.all()
    serializer_class = CompanyDataSourceSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["source_type", "verification_status", "active"]
    search_fields = ["name", "publisher", "slug"]
    ordering_fields = ["name", "reliability_score", "last_retrieved_at"]


class RawCompanyDatasetViewSet(ReadOnlyModelViewSet):
    queryset = RawCompanyDataset.objects.select_related("source").all()
    serializer_class = RawCompanyDatasetSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["source", "parsing_status", "schema_version"]
    search_fields = ["dataset_id", "original_filename", "checksum_sha256"]
    ordering_fields = ["retrieved_at", "row_count", "created_at"]
