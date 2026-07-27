from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schemes.models import EligibilityRule, Scheme
from apps.startups.models import StartupProfile

from .models import EligibilityVerificationSubmission
from .services.verification import (
    add_verification_evidence,
    create_verification_submission,
    verification_gate_statuses,
)
from .verification_serializers import (
    EligibilityVerificationEvidenceSerializer,
    EligibilityVerificationEvidenceUploadSerializer,
    EligibilityVerificationGateQuerySerializer,
    EligibilityVerificationSubmissionCreateSerializer,
    EligibilityVerificationSubmissionSerializer,
)


def _visible_profiles(user):
    if getattr(user, "is_staff", False):
        return StartupProfile.objects.all()
    return StartupProfile.objects.filter(owner=user)


def _visible_submissions(user):
    if getattr(user, "is_staff", False):
        return EligibilityVerificationSubmission.objects.all()
    return EligibilityVerificationSubmission.objects.filter(
        startup_profile__owner=user,
    )


def _raise_service_validation(
    exc: DjangoValidationError,
) -> None:
    if hasattr(exc, "message_dict"):
        raise DRFValidationError(exc.message_dict)
    raise DRFValidationError(exc.messages)


class EligibilityVerificationGateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = EligibilityVerificationGateQuerySerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        scheme = get_object_or_404(
            Scheme.objects.select_related("current_version"),
            pk=request_serializer.validated_data["scheme_id"],
        )

        if scheme.current_version is None:
            return Response(
                {"detail": ("Scheme has no published current version.")},
                status=status.HTTP_409_CONFLICT,
            )

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        gates = verification_gate_statuses(
            startup_profile=startup_profile,
            scheme_version=scheme.current_version,
            as_of_date=request_serializer.validated_data["as_of_date"],
        )

        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "scheme_id": str(scheme.id),
                "scheme_version_id": str(
                    scheme.current_version_id,
                ),
                "as_of_date": request_serializer.validated_data["as_of_date"].isoformat(),
                "gate_count": len(gates),
                "unresolved_count": sum(not gate["resolved"] for gate in gates),
                "gates": gates,
            },
            status=status.HTTP_200_OK,
        )


class EligibilityVerificationSubmissionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = EligibilityVerificationSubmissionCreateSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        scheme = get_object_or_404(
            Scheme.objects.select_related("current_version"),
            pk=request_serializer.validated_data["scheme_id"],
        )

        if scheme.current_version is None:
            return Response(
                {"detail": ("Scheme has no published current version.")},
                status=status.HTTP_409_CONFLICT,
            )

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        eligibility_rule = get_object_or_404(
            EligibilityRule.objects.filter(
                scheme_version=scheme.current_version,
            ),
            pk=request_serializer.validated_data["eligibility_rule_id"],
        )

        try:
            submission = create_verification_submission(
                startup_profile=startup_profile,
                scheme_version=scheme.current_version,
                eligibility_rule=eligibility_rule,
                submitted_by=request.user,
                claim_value=request_serializer.validated_data.get(
                    "claim_value",
                ),
                claim_text=request_serializer.validated_data["claim_text"],
            )
        except DjangoValidationError as exc:
            _raise_service_validation(exc)

        response_serializer = EligibilityVerificationSubmissionSerializer(
            submission,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class EligibilityVerificationEvidenceUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, submission_id):
        request_serializer = EligibilityVerificationEvidenceUploadSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        submission = get_object_or_404(
            _visible_submissions(request.user).select_related(
                "startup_profile",
            ),
            pk=submission_id,
        )

        try:
            evidence = add_verification_evidence(
                submission=submission,
                uploaded_by=request.user,
                uploaded_file=request_serializer.validated_data["file"],
            )
        except DjangoValidationError as exc:
            _raise_service_validation(exc)

        response_serializer = EligibilityVerificationEvidenceSerializer(
            evidence,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )
