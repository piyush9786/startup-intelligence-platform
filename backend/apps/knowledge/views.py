from rest_framework import status, viewsets
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import DocumentExtraction

from .models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalKnowledgeDataset,
    ExternalSchemeRecord,
    KnowledgeExtractionRun,
    SchemeCandidate,
)
from .serializers import (
    ExternalCapitalSupportRecordSerializer,
    ExternalCertificationRequirementRecordSerializer,
    ExternalSchemeRecordSerializer,
    KnowledgeExtractionRunSerializer,
    SchemeCandidateSerializer,
)
from .services import extract_knowledge
from .tasks import extract_knowledge_task


class KnowledgeExtractionRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = KnowledgeExtractionRunSerializer
    queryset = KnowledgeExtractionRun.objects.select_related(
        "extraction",
        "extraction__source_document",
        "extraction__source_document__source",
    )


class SchemeCandidateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = SchemeCandidateSerializer
    queryset = SchemeCandidate.objects.select_related(
        "run",
        "run__extraction",
        "run__extraction__source_document",
    ).prefetch_related(
        "evidence",
        "eligibility_rules",
        "benefit_items",
        "required_document_items",
        "application_steps",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        review_status = self.request.query_params.get("review_status")
        kind = self.request.query_params.get("kind")
        run_id = self.request.query_params.get("run")
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        if kind:
            queryset = queryset.filter(kind=kind)
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        return queryset


class ExternalSchemeRecordViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ExternalSchemeRecordSerializer
    filterset_fields = (
        "review_status",
        "central_state",
        "state",
        "funding_type",
    )
    search_fields = (
        "scheme_name",
        "ministry",
        "department",
        "sector",
        "industry",
        "eligibility",
    )
    ordering_fields = (
        "scheme_name",
        "updated_at",
        "review_status",
    )
    ordering = ("scheme_name",)

    queryset = (
        ExternalSchemeRecord.objects.select_related(
            "dataset",
            "matched_scheme",
        )
        .filter(
            dataset__is_active=True,
            matched_scheme__isnull=True,
        )
        .exclude(
            review_status=ExternalSchemeRecord.ReviewStatus.REJECTED,
        )
    )


class ExternalCapitalSupportRecordViewSet(
    viewsets.ReadOnlyModelViewSet
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = (
        ExternalCapitalSupportRecordSerializer
    )
    filterset_fields = (
        "review_status",
        "support_type",
        "funding_category",
        "state",
        "claimed_scheme_status",
    )
    search_fields = (
        "support_name",
        "scheme_name",
        "ministry",
        "implementing_agency",
        "funding_category",
        "industry",
        "eligible_entity",
        "funding_purpose",
    )
    ordering_fields = (
        "support_name",
        "minimum_amount",
        "maximum_amount",
        "updated_at",
        "review_status",
    )
    ordering = ("support_name",)

    queryset = (
        ExternalCapitalSupportRecord.objects
        .select_related(
            "dataset",
            "matched_scheme",
        )
        .filter(
            dataset__is_active=True,
            dataset__dataset_kind=(
                ExternalKnowledgeDataset
                .DatasetKind.CAPITAL_SUPPORT
            ),
            matched_scheme__isnull=True,
        )
        .exclude(
            review_status=(
                ExternalCapitalSupportRecord
                .ReviewStatus.REJECTED
            ),
        )
    )


class ExternalCertificationRequirementRecordViewSet(
    viewsets.ReadOnlyModelViewSet
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = (
        ExternalCertificationRequirementRecordSerializer
    )
    filterset_fields = (
        "review_status",
        "certificate_type",
        "requirement_level",
        "issuing_authority",
    )
    search_fields = (
        "certificate_name",
        "description",
        "industry",
        "startup_stage",
        "eligibility",
        "benefits",
        "issuing_authority",
    )
    ordering_fields = (
        "certificate_name",
        "updated_at",
        "review_status",
    )
    ordering = ("certificate_name",)

    queryset = (
        ExternalCertificationRequirementRecord.objects
        .select_related("dataset")
        .filter(
            dataset__is_active=True,
            dataset__dataset_kind=(
                ExternalKnowledgeDataset
                .DatasetKind.CERTIFICATION_REQUIREMENT
            ),
            display_eligible=True,
        )
        .exclude(
            review_status=(
                ExternalCertificationRequirementRecord
                .ReviewStatus.REJECTED
            ),
        )
    )


class ExtractKnowledgeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        extraction_id = request.data.get("extraction_id")
        document_id = request.data.get("document_id")
        force = bool(request.data.get("force", False))
        enqueue = bool(request.data.get("enqueue", False))
        if bool(extraction_id) == bool(document_id):
            return Response(
                {"detail": ("Provide exactly one of extraction_id or document_id.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = DocumentExtraction.objects.filter(status=DocumentExtraction.Status.SUCCEEDED)
        if extraction_id:
            queryset = queryset.filter(pk=extraction_id)
        else:
            queryset = queryset.filter(source_document_id=document_id)
        extraction = queryset.order_by("-created_at").first()
        if extraction is None:
            return Response(
                {"detail": "A successful extraction was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if enqueue:
            task = extract_knowledge_task.delay(str(extraction.id), force)
            return Response(
                {"task_id": task.id},
                status=status.HTTP_202_ACCEPTED,
            )
        try:
            result = extract_knowledge(extraction, force=force)
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "run_id": str(result.run.id),
                "candidate_count": result.candidate_count,
                "unchanged": result.unchanged,
            }
        )
