import ipaddress
import re
import socket
from tempfile import SpooledTemporaryFile
from urllib.parse import urljoin, urlsplit

import httpx
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.serializers import (
    RecommendationGenerationRunDetailSerializer,
    RecommendationSerializer,
)
from apps.recommendations.services import (
    RecommendationSetIntegrityError,
    get_current_recommendation_set,
)

from .models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from .serializers import (
    StartupAdvisorBriefingGenerationRequestSerializer,
    StartupAdvisorBriefingJobSerializer,
    StartupAdvisorBriefingSerializer,
    StartupAdvisorSnapshotGenerationRequestSerializer,
    StartupAdvisorSnapshotSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessRetrievalRequestSerializer,
)
from .services import (
    create_startup_advisor_snapshot,
)
from .services.advisor_briefing_jobs import (
    AdvisorBriefingJobDispatchError,
    queue_startup_advisor_briefing_job,
    reconcile_startup_advisor_briefing_job,
)


def _visible_profiles(user):
    return StartupProfile.objects.filter(owner=user)


def _visible_advisor_briefings(user):
    return StartupAdvisorBriefing.objects.filter(
        startup_profile__owner=user,
    )


def _visible_advisor_briefing_jobs(user):
    return StartupAdvisorBriefingJob.objects.filter(
        startup_profile__owner=user,
    )


def _visible_advisor_snapshots(user):
    return StartupAdvisorSnapshot.objects.filter(
        startup_profile__owner=user,
    )


def _resolve_target_profile(user, profile_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupProfile.objects.all(), pk=profile_id)
    return get_object_or_404(StartupProfile.objects.filter(owner=user), pk=profile_id)


def _resolve_target_snapshot(user, snapshot_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorSnapshot.objects.all(), pk=snapshot_id)
    return get_object_or_404(
        StartupAdvisorSnapshot.objects.filter(startup_profile__owner=user),
        pk=snapshot_id,
    )


def _resolve_target_job(user, job_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorBriefingJob.objects.all(), pk=job_id)
    return get_object_or_404(
        StartupAdvisorBriefingJob.objects.filter(startup_profile__owner=user),
        pk=job_id,
    )


def _resolve_target_briefing(user, briefing_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorBriefing.objects.all(), pk=briefing_id)
    return get_object_or_404(
        StartupAdvisorBriefing.objects.filter(startup_profile__owner=user),
        pk=briefing_id,
    )



ADVISOR_SOURCE_MAX_BYTES = (
    30 * 1024 * 1024
)

ADVISOR_SOURCE_REDIRECT_LIMIT = 4

ADVISOR_SOURCE_CHUNK_SIZE = (
    64 * 1024
)


class AdvisorSourceDownloadUpstreamError(
    APIException
):
    status_code = 502
    default_code = (
        "advisor_source_download_failed"
    )
    default_detail = (
        "The verified source could not "
        "be downloaded."
    )


class AdvisorSourceDownloadTooLarge(
    APIException
):
    status_code = 413
    default_code = (
        "advisor_source_too_large"
    )
    default_detail = (
        "The source document exceeds "
        "the download size limit."
    )


def _advisor_snapshot_recommendations(
    briefing,
):
    prompt_snapshot = (
        briefing.prompt_snapshot
        if isinstance(
            briefing.prompt_snapshot,
            dict,
        )
        else {}
    )

    source_input = (
        prompt_snapshot.get(
            "source_input",
            {},
        )
    )

    if not isinstance(
        source_input,
        dict,
    ):
        source_input = {}

    recommendations = (
        source_input.get(
            "recommendations",
            [],
        )
    )

    if isinstance(
        recommendations,
        list,
    ) and recommendations:
        return recommendations

    # Backward-compatible fallback for an
    # older persisted briefing shape.
    snapshot = getattr(
        briefing,
        "source_snapshot",
        None,
    )

    if snapshot is None:
        return []

    recommendations = getattr(
        snapshot,
        "recommendations_snapshot",
        [],
    )

    return (
        recommendations
        if isinstance(
            recommendations,
            list,
        )
        else []
    )


def _advisor_recommendation(
    briefing,
    recommendation_id,
):
    expected_id = str(
        recommendation_id
    )

    for recommendation in (
        _advisor_snapshot_recommendations(
            briefing
        )
    ):
        if not isinstance(
            recommendation,
            dict,
        ):
            continue

        if (
            str(
                recommendation.get(
                    "id",
                    "",
                )
            )
            == expected_id
        ):
            return recommendation

    raise NotFound(
        "The recommendation does not "
        "belong to this briefing."
    )


def _source_document_dict(
    recommendation,
):
    source_document = (
        recommendation.get(
            "source_document",
            {},
        )
    )

    return (
        source_document
        if isinstance(
            source_document,
            dict,
        )
        else {}
    )


def _looks_like_pdf_url(
    value,
):
    value = str(
        value or ""
    ).strip()

    if not value:
        return False

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    return parsed.path.lower().endswith(
        ".pdf"
    )


def _recommendation_source_url(
    recommendation,
):
    source_document = (
        _source_document_dict(
            recommendation
        )
    )

    candidates = [
        source_document.get(
            "download_url"
        ),
        source_document.get(
            "final_url"
        ),
        source_document.get(
            "source_url"
        ),
        recommendation.get(
            "official_url"
        ),
        recommendation.get(
            "application_url"
        ),
    ]

    candidates = [
        str(value).strip()
        for value in candidates
        if str(value or "").strip()
    ]

    if not candidates:
        raise NotFound(
            "No downloadable source is "
            "stored for this recommendation."
        )

    # Prefer an explicitly PDF-like URL when
    # more than one source is persisted.
    for candidate in candidates:
        if _looks_like_pdf_url(
            candidate
        ):
            return candidate

    return candidates[0]


def _validate_public_source_url(
    value,
):
    value = str(
        value or ""
    ).strip()

    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValidationError(
            "The persisted source URL "
            "is invalid."
        ) from exc

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValidationError(
            "Only HTTP and HTTPS source "
            "URLs may be downloaded."
        )

    if not parsed.hostname:
        raise ValidationError(
            "The persisted source URL "
            "has no hostname."
        )

    if (
        parsed.username
        or parsed.password
    ):
        raise ValidationError(
            "Credential-bearing source "
            "URLs are not allowed."
        )

    try:
        port = (
            parsed.port
            or (
                443
                if parsed.scheme
                == "https"
                else 80
            )
        )
    except ValueError as exc:
        raise ValidationError(
            "The persisted source URL "
            "contains an invalid port."
        ) from exc

    # Government/official source retrieval does
    # not require arbitrary internal ports.
    if port not in {
        80,
        443,
    }:
        raise ValidationError(
            "The persisted source URL "
            "uses a disallowed port."
        )

    hostname = parsed.hostname

    try:
        address_info = (
            socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        )
    except socket.gaierror as exc:
        raise AdvisorSourceDownloadUpstreamError(
            "The verified source hostname "
            "could not be resolved."
        ) from exc

    if not address_info:
        raise AdvisorSourceDownloadUpstreamError(
            "The verified source hostname "
            "could not be resolved."
        )

    for item in address_info:
        raw_address = str(
            item[4][0]
        ).split(
            "%",
            1,
        )[0]

        try:
            ip = ipaddress.ip_address(
                raw_address
            )
        except ValueError as exc:
            raise ValidationError(
                "The source hostname resolved "
                "to an invalid address."
            ) from exc

        # Reject localhost, private networks,
        # link-local, reserved, multicast,
        # CGNAT and other non-public targets.
        if not ip.is_global:
            raise ValidationError(
                "The verified source does not "
                "resolve to a public address."
            )

    return value


def _download_verified_pdf(
    source_url,
):
    current_url = str(
        source_url
    ).strip()

    timeout = httpx.Timeout(
        connect=8.0,
        read=45.0,
        write=10.0,
        pool=10.0,
    )

    headers = {
        "Accept": (
            "application/pdf,"
            "application/octet-stream;"
            "q=0.9,*/*;q=0.5"
        ),
        "User-Agent": (
            "StartupIntelligencePlatform/"
            "1.0 verified-source-downloader"
        ),
    }

    # trust_env=False prevents environment proxy
    # variables from silently routing this
    # security-sensitive request elsewhere.
    with httpx.Client(
        timeout=timeout,
        headers=headers,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for _ in range(
            ADVISOR_SOURCE_REDIRECT_LIMIT
            + 1
        ):
            _validate_public_source_url(
                current_url
            )

            try:
                with client.stream(
                    "GET",
                    current_url,
                ) as upstream:
                    if upstream.status_code in {
                        301,
                        302,
                        303,
                        307,
                        308,
                    }:
                        location = (
                            upstream.headers.get(
                                "location"
                            )
                        )

                        if not location:
                            raise (
                                AdvisorSourceDownloadUpstreamError(
                                    "The verified source "
                                    "returned an invalid "
                                    "redirect."
                                )
                            )

                        current_url = urljoin(
                            current_url,
                            location,
                        )

                        continue

                    if (
                        upstream.status_code
                        < 200
                        or upstream.status_code
                        >= 300
                    ):
                        raise (
                            AdvisorSourceDownloadUpstreamError(
                                "The verified source "
                                f"returned HTTP "
                                f"{upstream.status_code}."
                            )
                        )

                    declared_length = (
                        upstream.headers.get(
                            "content-length"
                        )
                    )

                    if declared_length:
                        try:
                            if (
                                int(
                                    declared_length
                                )
                                > ADVISOR_SOURCE_MAX_BYTES
                            ):
                                raise (
                                    AdvisorSourceDownloadTooLarge()
                                )
                        except ValueError:
                            pass

                    output = (
                        SpooledTemporaryFile(
                            max_size=(
                                2
                                * 1024
                                * 1024
                            ),
                            mode="w+b",
                        )
                    )

                    total = 0

                    try:
                        for chunk in (
                            upstream.iter_bytes(
                                ADVISOR_SOURCE_CHUNK_SIZE
                            )
                        ):
                            if not chunk:
                                continue

                            total += len(
                                chunk
                            )

                            if (
                                total
                                > ADVISOR_SOURCE_MAX_BYTES
                            ):
                                raise (
                                    AdvisorSourceDownloadTooLarge()
                                )

                            output.write(
                                chunk
                            )

                        if total == 0:
                            raise (
                                AdvisorSourceDownloadUpstreamError(
                                    "The verified source "
                                    "returned an empty "
                                    "document."
                                )
                            )

                        output.seek(0)

                        signature = (
                            output.read(
                                min(
                                    1024,
                                    total,
                                )
                            )
                        )

                        # Validate the bytes, not merely
                        # the URL extension or Content-Type.
                        if (
                            b"%PDF-"
                            not in signature
                        ):
                            raise (
                                UnsupportedMediaType(
                                    "The verified source "
                                    "is not a PDF document."
                                )
                            )

                        output.seek(0)

                        return (
                            output,
                            current_url,
                            total,
                        )

                    except Exception:
                        output.close()
                        raise

            except (
                APIException,
                UnsupportedMediaType,
            ):
                raise
            except httpx.TimeoutException as exc:
                raise AdvisorSourceDownloadUpstreamError(
                    "The verified source timed out."
                ) from exc
            except httpx.HTTPError as exc:
                raise AdvisorSourceDownloadUpstreamError(
                    "The verified source could not "
                    "be retrieved."
                ) from exc

    raise AdvisorSourceDownloadUpstreamError(
        "The verified source exceeded "
        "the redirect limit."
    )


def _advisor_pdf_filename(
    recommendation,
):
    source_document = (
        _source_document_dict(
            recommendation
        )
    )

    base_name = str(
        source_document.get(
            "title"
        )
        or recommendation.get(
            "scheme_name"
        )
        or "verified-source"
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        base_name,
    ).strip(
        ".-_"
    )

    if not safe_name:
        safe_name = (
            "verified-source"
        )

    if not safe_name.lower().endswith(
        ".pdf"
    ):
        safe_name += ".pdf"

    return safe_name[:180]



class StartupAdvisorCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        readiness_assessment = (
            StartupReadinessAssessment.objects.filter(
                startup_profile=startup_profile,
            )
            .select_related(
                "startup_profile",
                "requested_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )
        readiness_action_plan = (
            StartupReadinessActionPlan.objects.filter(
                startup_profile=startup_profile,
            )
            .select_related(
                "startup_profile",
                "source_assessment",
                "requested_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

        try:
            current_recommendations = get_current_recommendation_set(
                startup_profile=startup_profile,
            )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        assessment_data = (
            StartupReadinessAssessmentSerializer(
                readiness_assessment,
            ).data
            if readiness_assessment is not None
            else None
        )
        action_plan_data = (
            StartupReadinessActionPlanSerializer(
                readiness_action_plan,
            ).data
            if readiness_action_plan is not None
            else None
        )
        generation_data = (
            RecommendationGenerationRunDetailSerializer(
                current_recommendations.generation_run,
            ).data
            if current_recommendations.generation_run is not None
            else None
        )
        recommendation_data = RecommendationSerializer(
            current_recommendations.recommendations,
            many=True,
        ).data

        return Response(
            {
                "startup_profile": {
                    "id": str(startup_profile.id),
                    "startup_name": startup_profile.startup_name,
                    "legal_name": startup_profile.legal_name,
                    "stage": startup_profile.stage,
                    "state": startup_profile.state,
                    "district": startup_profile.district,
                },
                "readiness": {
                    "has_assessment": (readiness_assessment is not None),
                    "assessment": assessment_data,
                },
                "action_plan": {
                    "has_action_plan": (readiness_action_plan is not None),
                    "action_plan": action_plan_data,
                },
                "recommendations": {
                    "has_generation": (current_recommendations.has_generation),
                    "generation": generation_data,
                    "recommendation_count": len(
                        current_recommendations.recommendations,
                    ),
                    "recommendations": recommendation_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorSnapshotGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupAdvisorSnapshotGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        try:
            snapshot = create_startup_advisor_snapshot(
                startup_profile=startup_profile,
                requested_by=request.user,
            )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            StartupAdvisorSnapshotSerializer(snapshot).data,
            status=status.HTTP_201_CREATED,
        )


class StartupAdvisorBriefingGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupAdvisorBriefingGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        source_snapshot = _resolve_target_snapshot(
            request.user,
            request_serializer.validated_data["advisor_snapshot_id"],
        )

        try:
            job, created = queue_startup_advisor_briefing_job(
                source_snapshot=source_snapshot,
                requested_by=request.user,
            )
        except AdvisorBriefingJobDispatchError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "created": created,
                "job": StartupAdvisorBriefingJobSerializer(job).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class StartupAdvisorBriefingJobCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        job = (
            _visible_advisor_briefing_jobs(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
                "briefing",
            )
            .order_by("-created_at", "-id")
            .first()
        )

        if job is not None:
            job = reconcile_startup_advisor_briefing_job(
                job_id=job.id,
            )

        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_job": job is not None,
                "job": (StartupAdvisorBriefingJobSerializer(job).data if job is not None else None),
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = _resolve_target_job(request.user, job_id)
        job = reconcile_startup_advisor_briefing_job(
            job_id=job.id,
        )

        return Response(
            StartupAdvisorBriefingJobSerializer(job).data,
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )
        briefing = (
            _visible_advisor_briefings(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
            )
            .order_by("-completed_at", "-created_at", "-id")
            .first()
        )
        data = StartupAdvisorBriefingSerializer(briefing).data if briefing is not None else None
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_briefing": briefing is not None,
                "briefing": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )
        briefings_qs = (
            StartupAdvisorBriefing.objects.all()
            if request.user.is_staff
            else _visible_advisor_briefings(request.user)
        )
        briefings = (
            briefings_qs.filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
            )
            .order_by("-completed_at", "-created_at", "-id")
        )
        data = StartupAdvisorBriefingSerializer(
            briefings,
            many=True,
        ).data
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "count": len(data),
                "briefings": data,
            },
            status=status.HTTP_200_OK,
        )



class StartupAdvisorRecommendationSourceDownloadView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]

    def get(
        self,
        request,
        briefing_id,
        recommendation_id,
    ):
        # Ownership/visibility is enforced by
        # the existing Advisor resolver.
        briefing = (
            _resolve_target_briefing(
                request.user,
                briefing_id,
            )
        )

        recommendation = (
            _advisor_recommendation(
                briefing,
                recommendation_id,
            )
        )

        source_url = (
            _recommendation_source_url(
                recommendation
            )
        )

        (
            pdf_file,
            final_url,
            size_bytes,
        ) = _download_verified_pdf(
            source_url
        )

        response = FileResponse(
            pdf_file,
            as_attachment=True,
            filename=(
                _advisor_pdf_filename(
                    recommendation
                )
            ),
            content_type="application/pdf",
        )

        response[
            "Content-Length"
        ] = str(size_bytes)

        response[
            "X-Content-Type-Options"
        ] = "nosniff"

        response[
            "Cache-Control"
        ] = "private, no-store"

        response[
            "X-Advisor-Source"
        ] = "verified-recommendation"

        return response



class StartupAdvisorBriefingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, briefing_id):
        briefing = _resolve_target_briefing(request.user, briefing_id)
        return Response(
            StartupAdvisorBriefingSerializer(briefing).data,
            status=status.HTTP_200_OK,
        )
