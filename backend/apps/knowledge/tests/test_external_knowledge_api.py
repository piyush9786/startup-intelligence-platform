import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalKnowledgeDataset,
)
from apps.schemes.models import Authority, Scheme

pytestmark = pytest.mark.django_db

CAPITAL_ENDPOINT = (
    "/api/v1/knowledge/external-capital-support/"
)
CERTIFICATION_ENDPOINT = (
    "/api/v1/knowledge/"
    "external-certification-requirements/"
)


def create_dataset(
    *,
    dataset_key: str,
    dataset_kind: str,
    is_active: bool = True,
) -> ExternalKnowledgeDataset:
    return ExternalKnowledgeDataset.objects.create(
        dataset_kind=dataset_kind,
        dataset_key=dataset_key,
        dataset_name=f"Dataset {dataset_key}",
        source_filename=f"{dataset_key}.json",
        source_row_count=1,
        record_count=1,
        normalization_version="test-v1",
        content_sha256="a" * 64,
        is_active=is_active,
    )


def create_capital_record(
    *,
    dataset: ExternalKnowledgeDataset,
    external_id: str,
    support_name: str,
    review_status: str = (
        ExternalCapitalSupportRecord
        .ReviewStatus.NEEDS_REVIEW
    ),
    support_type: str = "Grant",
    funding_category: str = "Grant",
    state: str = "Pan India",
    matched_scheme: Scheme | None = None,
) -> ExternalCapitalSupportRecord:
    return ExternalCapitalSupportRecord.objects.create(
        dataset=dataset,
        external_id=external_id,
        support_name=support_name,
        support_type=support_type,
        scheme_name=support_name,
        normalized_name=support_name.lower(),
        ministry="Example Ministry",
        implementing_agency="Example Agency",
        funding_category=funding_category,
        raw_minimum_amount="INR 1 lakh",
        raw_maximum_amount="INR 10 lakh",
        currency="INR",
        startup_stage=["Idea"],
        industry=["Technology"],
        eligible_entity="DPIIT-recognised startup",
        state=state,
        funding_purpose="Startup growth",
        claimed_scheme_status="Active",
        source_priority_score=9,
        source_ai_recommendation_weight="0.90000",
        remarks="Example remark",
        matched_external_scheme_ids=["SCH001"],
        matched_scheme=matched_scheme,
        review_status=review_status,
        review_notes="Internal review note",
        quality_warnings=[],
        raw_row={
            "private_source_column": (
                "must not be exposed"
            ),
        },
        record_sha256=(
            external_id.lower().ljust(64, "0")[:64]
        ),
    )


def create_certification_record(
    *,
    dataset: ExternalKnowledgeDataset,
    external_id: str,
    certificate_name: str,
    display_eligible: bool = True,
    review_status: str = (
        ExternalCertificationRequirementRecord
        .ReviewStatus.NEEDS_REVIEW
    ),
    certificate_type: str = "Registration",
    requirement_level: str = "Mandatory",
    issuing_authority: str = "Example Authority",
) -> ExternalCertificationRequirementRecord:
    return (
        ExternalCertificationRequirementRecord.objects.create(
            dataset=dataset,
            external_id=external_id,
            certificate_name=certificate_name,
            normalized_name=certificate_name.lower(),
            certificate_type=certificate_type,
            description="Example certification",
            industry=["All Industries"],
            startup_stage=["Idea"],
            requirement_level=requirement_level,
            eligibility="Example eligibility",
            benefits="Example benefits",
            validity="Valid while active",
            renewal_period="As applicable",
            issuing_authority=issuing_authority,
            official_document_text="Official guidance",
            official_apply_url=(
                "https://example.gov.in/apply"
            ),
            source_priority_score=10,
            display_eligible=display_eligible,
            review_status=review_status,
            review_notes="Internal review note",
            quality_warnings=[],
            raw_row={
                "private_source_column": (
                    "must not be exposed"
                ),
            },
            record_sha256=(
                external_id.lower().ljust(64, "0")[:64]
            ),
        )
    )


def response_results(response) -> list[dict]:
    payload = response.json()

    if isinstance(payload, list):
        return payload

    return payload["results"]


def test_capital_endpoint_exposes_only_visible_records():
    capital_kind = (
        ExternalKnowledgeDataset
        .DatasetKind.CAPITAL_SUPPORT
    )
    certification_kind = (
        ExternalKnowledgeDataset
        .DatasetKind.CERTIFICATION_REQUIREMENT
    )

    active_dataset = create_dataset(
        dataset_key="active-capital",
        dataset_kind=capital_kind,
    )
    inactive_dataset = create_dataset(
        dataset_key="inactive-capital",
        dataset_kind=capital_kind,
        is_active=False,
    )
    wrong_kind_dataset = create_dataset(
        dataset_key="wrong-kind-capital",
        dataset_kind=certification_kind,
    )

    visible = create_capital_record(
        dataset=active_dataset,
        external_id="CAP001",
        support_name="Visible Capital Support",
    )
    verified = create_capital_record(
        dataset=active_dataset,
        external_id="CAP002",
        support_name="Verified Capital Support",
        review_status=(
            ExternalCapitalSupportRecord
            .ReviewStatus.VERIFIED
        ),
    )
    create_capital_record(
        dataset=active_dataset,
        external_id="CAP003",
        support_name="Rejected Capital Support",
        review_status=(
            ExternalCapitalSupportRecord
            .ReviewStatus.REJECTED
        ),
    )
    create_capital_record(
        dataset=inactive_dataset,
        external_id="CAP004",
        support_name="Inactive Capital Support",
    )
    create_capital_record(
        dataset=wrong_kind_dataset,
        external_id="CAP005",
        support_name="Wrong Dataset Kind",
    )

    authority = Authority.objects.create(
        name="Matched Authority",
    )
    scheme = Scheme.objects.create(
        canonical_name="Matched Capital Scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    create_capital_record(
        dataset=active_dataset,
        external_id="CAP006",
        support_name="Matched Canonical Capital",
        matched_scheme=scheme,
    )

    response = APIClient().get(CAPITAL_ENDPOINT)

    assert response.status_code == 200

    returned_ids = {
        item["id"]
        for item in response_results(response)
    }

    assert returned_ids == {
        str(visible.id),
        str(verified.id),
    }


def test_capital_response_is_safe_and_filterable():
    dataset = create_dataset(
        dataset_key="capital-search",
        dataset_kind=(
            ExternalKnowledgeDataset
            .DatasetKind.CAPITAL_SUPPORT
        ),
    )

    grant = create_capital_record(
        dataset=dataset,
        external_id="CAP001",
        support_name="Women Founder Grant",
        support_type="Grant",
        funding_category="Grant",
    )
    create_capital_record(
        dataset=dataset,
        external_id="CAP002",
        support_name="State Startup Loan",
        support_type="Loan",
        funding_category="Debt",
        state="Karnataka",
    )

    response = APIClient().get(
        CAPITAL_ENDPOINT,
        {
            "search": "Women",
            "support_type": "Grant",
        },
    )

    assert response.status_code == 200

    results = response_results(response)

    assert len(results) == 1
    assert results[0]["id"] == str(grant.id)

    item = results[0]

    assert item["source_type"] == "external"
    assert item["record_type"] == "capital_support"
    assert item["verification_label"] == "Needs review"
    assert item["dataset_key"] == "capital-search"
    assert "Verify funding terms" in item["disclaimer"]

    for internal_field in (
        "raw_row",
        "record_sha256",
        "review_notes",
        "source_priority_score",
        "source_ai_recommendation_weight",
        "matched_external_scheme_ids",
        "matched_external_schemes",
        "matched_scheme",
        "source_row_number",
    ):
        assert internal_field not in item

    response = APIClient().get(
        CAPITAL_ENDPOINT,
        {
            "state": "Karnataka",
        },
    )

    assert response.status_code == 200
    assert response_results(response)[0][
        "external_id"
    ] == "CAP002"


def test_certification_endpoint_exposes_only_displayable_records():
    certification_kind = (
        ExternalKnowledgeDataset
        .DatasetKind.CERTIFICATION_REQUIREMENT
    )
    capital_kind = (
        ExternalKnowledgeDataset
        .DatasetKind.CAPITAL_SUPPORT
    )

    active_dataset = create_dataset(
        dataset_key="active-certifications",
        dataset_kind=certification_kind,
    )
    inactive_dataset = create_dataset(
        dataset_key="inactive-certifications",
        dataset_kind=certification_kind,
        is_active=False,
    )
    wrong_kind_dataset = create_dataset(
        dataset_key="wrong-kind-certification",
        dataset_kind=capital_kind,
    )

    visible = create_certification_record(
        dataset=active_dataset,
        external_id="CERT001",
        certificate_name="Visible Registration",
    )
    verified = create_certification_record(
        dataset=active_dataset,
        external_id="CERT002",
        certificate_name="Verified Registration",
        review_status=(
            ExternalCertificationRequirementRecord
            .ReviewStatus.VERIFIED
        ),
    )
    create_certification_record(
        dataset=active_dataset,
        external_id="CERT003",
        certificate_name="Hidden Registration",
        display_eligible=False,
    )
    create_certification_record(
        dataset=active_dataset,
        external_id="CERT004",
        certificate_name="Rejected Registration",
        display_eligible=False,
        review_status=(
            ExternalCertificationRequirementRecord
            .ReviewStatus.REJECTED
        ),
    )
    create_certification_record(
        dataset=inactive_dataset,
        external_id="CERT005",
        certificate_name="Inactive Registration",
    )
    create_certification_record(
        dataset=wrong_kind_dataset,
        external_id="CERT006",
        certificate_name="Wrong Dataset Kind",
    )

    response = APIClient().get(
        CERTIFICATION_ENDPOINT,
    )

    assert response.status_code == 200

    returned_ids = {
        item["id"]
        for item in response_results(response)
    }

    assert returned_ids == {
        str(visible.id),
        str(verified.id),
    }


def test_certification_response_is_safe_and_filterable():
    dataset = create_dataset(
        dataset_key="certification-search",
        dataset_kind=(
            ExternalKnowledgeDataset
            .DatasetKind.CERTIFICATION_REQUIREMENT
        ),
    )

    registration = create_certification_record(
        dataset=dataset,
        external_id="CERT001",
        certificate_name="GST Registration",
        certificate_type="Registration",
        issuing_authority="GST Authority",
    )
    create_certification_record(
        dataset=dataset,
        external_id="CERT002",
        certificate_name="ISO Quality Certificate",
        certificate_type="Certification",
        requirement_level="Optional",
        issuing_authority="ISO Body",
    )

    response = APIClient().get(
        CERTIFICATION_ENDPOINT,
        {
            "search": "GST",
            "certificate_type": "Registration",
        },
    )

    assert response.status_code == 200

    results = response_results(response)

    assert len(results) == 1
    assert results[0]["id"] == str(registration.id)

    item = results[0]

    assert item["source_type"] == "external"
    assert (
        item["record_type"]
        == "certification_requirement"
    )
    assert item["verification_label"] == "Needs review"
    assert item["display_eligible"] is True
    assert item["dataset_key"] == "certification-search"
    assert "issuing authority" in item["disclaimer"]

    for internal_field in (
        "raw_row",
        "record_sha256",
        "review_notes",
        "source_priority_score",
        "source_row_number",
    ):
        assert internal_field not in item

    response = APIClient().get(
        CERTIFICATION_ENDPOINT,
        {
            "issuing_authority": "ISO Body",
        },
    )

    assert response.status_code == 200
    assert response_results(response)[0][
        "external_id"
    ] == "CERT002"


@pytest.mark.parametrize(
    "endpoint",
    [
        CAPITAL_ENDPOINT,
        CERTIFICATION_ENDPOINT,
    ],
)
def test_external_knowledge_endpoints_are_read_only(
    endpoint,
):
    anonymous_client = APIClient()

    assert (
        anonymous_client.post(endpoint, {}).status_code
        == 401
    )

    user = get_user_model().objects.create_user(
        username=(
            "external-knowledge-api-user-"
            + endpoint.split("/")[-2]
        ),
        email=(
            endpoint.split("/")[-2]
            + "@example.com"
        ),
        password="test-password",
    )

    authenticated_client = APIClient()
    authenticated_client.force_authenticate(user=user)

    assert (
        authenticated_client.post(
            endpoint,
            {},
        ).status_code
        == 405
    )
    assert (
        authenticated_client.put(
            f"{endpoint}unknown/",
            {},
        ).status_code
        == 405
    )
    assert (
        authenticated_client.delete(
            f"{endpoint}unknown/",
        ).status_code
        == 405
    )
