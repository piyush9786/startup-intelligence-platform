import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.knowledge.models import (
    ExternalSchemeDataset,
    ExternalSchemeRecord,
)
from apps.schemes.models import Authority, Scheme

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/v1/knowledge/external-schemes/"


def create_dataset(
    *,
    dataset_key: str,
    is_active: bool = True,
) -> ExternalSchemeDataset:
    return ExternalSchemeDataset.objects.create(
        dataset_key=dataset_key,
        dataset_name=f"Dataset {dataset_key}",
        source_filename=f"{dataset_key}.json",
        source_row_count=1,
        record_count=1,
        normalization_version="test-v1",
        content_sha256="a" * 64,
        is_active=is_active,
    )


def create_record(
    *,
    dataset: ExternalSchemeDataset,
    external_id: str,
    scheme_name: str,
    review_status: str = ExternalSchemeRecord.ReviewStatus.NEEDS_REVIEW,
    matched_scheme: Scheme | None = None,
    state: str = "All India",
    funding_type: str = "Grant",
) -> ExternalSchemeRecord:
    return ExternalSchemeRecord.objects.create(
        dataset=dataset,
        external_id=external_id,
        scheme_name=scheme_name,
        normalized_name=scheme_name.lower(),
        ministry="Example Ministry",
        department="Example Department",
        sector="Startup",
        startup_stage=["Idea"],
        startup_type="Startup",
        industry=["Technology"],
        central_state="Central",
        state=state,
        funding_type=funding_type,
        funding_amount="Up to INR 10 lakh",
        financial_instrument="Grant",
        eligibility="Example eligibility",
        documents_required=["Registration certificate"],
        application_process="Apply online",
        official_application_url="https://example.gov.in/apply",
        source_portal="Example portal",
        quality_warnings=[],
        record_sha256=external_id.lower().ljust(64, "0")[:64],
        review_status=review_status,
        matched_scheme=matched_scheme,
    )


def response_results(response) -> list[dict]:
    payload = response.json()

    if isinstance(payload, list):
        return payload

    return payload["results"]


def test_anonymous_user_can_list_visible_external_schemes():
    active_dataset = create_dataset(
        dataset_key="active-dataset",
    )
    inactive_dataset = create_dataset(
        dataset_key="inactive-dataset",
        is_active=False,
    )

    visible = create_record(
        dataset=active_dataset,
        external_id="SCH001",
        scheme_name="Visible Needs Review Scheme",
    )
    verified = create_record(
        dataset=active_dataset,
        external_id="SCH002",
        scheme_name="Visible Verified Scheme",
        review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
    )
    create_record(
        dataset=active_dataset,
        external_id="SCH003",
        scheme_name="Rejected Scheme",
        review_status=ExternalSchemeRecord.ReviewStatus.REJECTED,
    )
    create_record(
        dataset=inactive_dataset,
        external_id="SCH004",
        scheme_name="Inactive Dataset Scheme",
    )

    authority = Authority.objects.create(
        name="Matched Authority",
    )
    canonical_scheme = Scheme.objects.create(
        canonical_name="Matched Canonical Scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    create_record(
        dataset=active_dataset,
        external_id="SCH005",
        scheme_name="Already Matched Scheme",
        matched_scheme=canonical_scheme,
    )

    response = APIClient().get(ENDPOINT)

    assert response.status_code == 200

    results = response_results(response)
    returned_ids = {item["id"] for item in results}

    assert returned_ids == {
        str(visible.id),
        str(verified.id),
    }


def test_external_scheme_response_is_public_safe():
    dataset = create_dataset(
        dataset_key="safe-response",
    )
    record = create_record(
        dataset=dataset,
        external_id="SCH001",
        scheme_name="Public External Scheme",
    )
    record.raw_row = {
        "private_source_column": "must not be exposed",
    }
    record.review_notes = "Internal review note"
    record.save(
        update_fields=[
            "raw_row",
            "review_notes",
            "updated_at",
        ],
    )

    response = APIClient().get(ENDPOINT)

    assert response.status_code == 200

    item = response_results(response)[0]

    assert item["scheme_name"] == "Public External Scheme"
    assert item["source_type"] == "external"
    assert item["verification_label"] == "Needs review"
    assert item["dataset_key"] == "safe-response"
    assert "Verify details on the official source" in item["disclaimer"]

    assert "raw_row" not in item
    assert "record_sha256" not in item
    assert "review_notes" not in item
    assert "external_ids" not in item
    assert "source_rows" not in item


def test_verified_external_scheme_has_source_review_label():
    dataset = create_dataset(
        dataset_key="reviewed-response",
    )
    create_record(
        dataset=dataset,
        external_id="SCH001",
        scheme_name="Source Reviewed Scheme",
        review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
    )

    response = APIClient().get(ENDPOINT)

    assert response.status_code == 200
    item = response_results(response)[0]

    assert item["verification_label"] == "Official source reviewed"
    assert "discovery-only" in item["disclaimer"]
    assert "current call dates and terms" in item["disclaimer"]


def test_external_scheme_list_supports_search_and_filters():
    dataset = create_dataset(
        dataset_key="search-filter",
    )

    create_record(
        dataset=dataset,
        external_id="SCH001",
        scheme_name="Women Founder Grant",
        state="All India",
        funding_type="Grant",
    )
    create_record(
        dataset=dataset,
        external_id="SCH002",
        scheme_name="State Startup Loan",
        state="Karnataka",
        funding_type="Loan",
    )

    client = APIClient()

    response = client.get(
        ENDPOINT,
        {
            "search": "Women",
            "funding_type": "Grant",
        },
    )

    assert response.status_code == 200

    results = response_results(response)

    assert len(results) == 1
    assert results[0]["external_id"] == "SCH001"

    response = client.get(
        ENDPOINT,
        {
            "state": "Karnataka",
        },
    )

    assert response.status_code == 200

    results = response_results(response)

    assert len(results) == 1
    assert results[0]["external_id"] == "SCH002"


def test_external_scheme_endpoint_is_read_only():
    dataset = create_dataset(
        dataset_key="read-only",
    )
    create_record(
        dataset=dataset,
        external_id="SCH001",
        scheme_name="Read Only Scheme",
    )

    anonymous_client = APIClient()

    # Unsafe anonymous requests are rejected by
    # IsAuthenticatedOrReadOnly before method routing.
    assert anonymous_client.post(ENDPOINT, {}).status_code == 401

    user = get_user_model().objects.create_user(
        username="external-scheme-api-user",
        email="external-scheme-api@example.com",
        password="test-password",
    )

    authenticated_client = APIClient()
    authenticated_client.force_authenticate(user=user)

    # The viewset exposes list and retrieve actions only.
    assert authenticated_client.post(ENDPOINT, {}).status_code == 405
    assert (
        authenticated_client.put(
            f"{ENDPOINT}unknown/",
            {},
        ).status_code
        == 405
    )
    assert (
        authenticated_client.delete(
            f"{ENDPOINT}unknown/",
        ).status_code
        == 405
    )
