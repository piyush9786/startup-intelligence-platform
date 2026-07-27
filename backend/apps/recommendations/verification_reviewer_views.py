from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    PermissionDenied,
)
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.sources.services.storage import stream_object

from .models import (
    EligibilityVerificationEvidence,
    EligibilityVerificationSubmission,
)
from .services.verification import (
    review_verification_submission,
    reviewer_verification_queue,
)
from .verification_reviewer_serializers import (
    EligibilityVerificationDecisionCreateSerializer,
    EligibilityVerificationDecisionSerializer,
    EligibilityVerificationReviewerQueueQuerySerializer,
)

REVIEWER_ROLES = {
    User.Role.REVIEWER,
    User.Role.ADMIN,
}


def _require_reviewer(user) -> None:
    if not user.is_active or (not user.is_superuser and user.role not in REVIEWER_ROLES):
        raise PermissionDenied("Reviewer or administrator access is required.")


def _raise_service_validation(
    exc: DjangoValidationError,
) -> None:
    if hasattr(exc, "message_dict"):
        raise DRFValidationError(exc.message_dict)
    raise DRFValidationError(exc.messages)


class EligibilityVerificationReviewerQueueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_reviewer(request.user)

        request_serializer = EligibilityVerificationReviewerQueueQuerySerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        submissions = reviewer_verification_queue(
            as_of_date=request_serializer.validated_data["as_of_date"],
        )

        return Response(
            {
                "as_of_date": request_serializer.validated_data["as_of_date"].isoformat(),
                "count": len(submissions),
                "submissions": submissions,
            },
            status=status.HTTP_200_OK,
        )


class EligibilityVerificationReviewerDecisionCreateView(
    APIView,
):
    permission_classes = [IsAuthenticated]

    def post(self, request, submission_id):
        _require_reviewer(request.user)

        request_serializer = EligibilityVerificationDecisionCreateSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        submission = get_object_or_404(
            EligibilityVerificationSubmission.objects.select_related(
                "startup_profile",
                "scheme_version",
                "eligibility_rule",
            ),
            pk=submission_id,
        )

        try:
            decision = review_verification_submission(
                submission=submission,
                reviewer=request.user,
                outcome=request_serializer.validated_data["outcome"],
                verified_value=(
                    request_serializer.validated_data.get(
                        "verified_value",
                    )
                ),
                review_notes=request_serializer.validated_data["review_notes"],
                valid_from=request_serializer.validated_data["valid_from"],
                expires_on=request_serializer.validated_data.get(
                    "expires_on",
                ),
            )
        except DjangoValidationError as exc:
            _raise_service_validation(exc)

        response_serializer = EligibilityVerificationDecisionSerializer(
            decision,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class EligibilityVerificationReviewerEvidenceDownloadView(
    APIView,
):
    permission_classes = [IsAuthenticated]

    def get(self, request, evidence_id):
        _require_reviewer(request.user)

        evidence = get_object_or_404(
            EligibilityVerificationEvidence.objects.select_related(
                "submission",
            ),
            pk=evidence_id,
        )

        content = stream_object(
            evidence.storage_key,
            bucket_name=(settings.MINIO_BUCKET_STARTUP_EVIDENCE),
        )

        response = StreamingHttpResponse(
            content,
            content_type=(evidence.mime_type or "application/octet-stream"),
        )
        response["Content-Disposition"] = content_disposition_header(
            True,
            evidence.filename,
        )
        response["Content-Length"] = evidence.size_bytes
        return response
