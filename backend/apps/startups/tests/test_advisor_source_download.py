from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from rest_framework.exceptions import (
    NotFound,
    ValidationError,
)
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from apps.startups.advisor_views import (
    StartupAdvisorRecommendationSourceDownloadView,
    _advisor_recommendation,
    _looks_like_pdf_url,
    _validate_public_source_url,
)


def fake_briefing():
    recommendation_id = uuid4()

    briefing = SimpleNamespace(
        prompt_snapshot={
            "source_input": {
                "recommendations": [
                    {
                        "id": str(
                            recommendation_id
                        ),
                        "scheme_name": (
                            "Verified Scheme"
                        ),
                        "official_url": (
                            "https://example.com/"
                            "scheme"
                        ),
                        "source_document": {
                            "title": (
                                "Official Scheme PDF"
                            ),
                            "final_url": (
                                "https://example.com/"
                                "scheme.pdf"
                            ),
                            "status": "verified",
                        },
                    }
                ]
            }
        },
        source_snapshot=None,
    )

    return (
        briefing,
        recommendation_id,
    )


def test_pdf_url_detection():
    assert _looks_like_pdf_url(
        "https://example.com/file.pdf"
    )

    assert not _looks_like_pdf_url(
        "https://example.com/page"
    )


def test_private_source_address_is_rejected():
    with pytest.raises(
        ValidationError
    ):
        _validate_public_source_url(
            "http://127.0.0.1/private.pdf"
        )


def test_recommendation_must_belong_to_briefing():
    briefing, _ = fake_briefing()

    with pytest.raises(NotFound):
        _advisor_recommendation(
            briefing,
            uuid4(),
        )


def test_authenticated_download_streams_pdf():
    briefing, recommendation_id = (
        fake_briefing()
    )

    briefing_id = uuid4()

    request = (
        APIRequestFactory().get(
            "/source-download/"
        )
    )

    force_authenticate(
        request,
        user=SimpleNamespace(
            is_authenticated=True,
            is_staff=False,
        ),
    )

    pdf_bytes = (
        b"%PDF-1.7\n"
        b"test document\n"
        b"%%EOF\n"
    )

    with (
        patch(
            "apps.startups.advisor_views."
            "_resolve_target_briefing",
            return_value=briefing,
        ),
        patch(
            "apps.startups.advisor_views."
            "_download_verified_pdf",
            return_value=(
                BytesIO(pdf_bytes),
                (
                    "https://example.com/"
                    "scheme.pdf"
                ),
                len(pdf_bytes),
            ),
        ),
    ):
        response = (
            StartupAdvisorRecommendationSourceDownloadView
            .as_view()(
                request,
                briefing_id=briefing_id,
                recommendation_id=(
                    recommendation_id
                ),
            )
        )

    assert response.status_code == 200

    assert (
        response["Content-Type"]
        == "application/pdf"
    )

    assert (
        "attachment"
        in response[
            "Content-Disposition"
        ]
    )

    assert (
        response[
            "X-Content-Type-Options"
        ]
        == "nosniff"
    )
