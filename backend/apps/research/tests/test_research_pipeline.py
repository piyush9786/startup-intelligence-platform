"""End-to-end tests for research requests and report generation."""
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status

from apps.companies.models import Company
from apps.research.models import (
    ResearchRequest,
    ResearchSearchQuery,
    StartupResearchReport,
)
from apps.research.services.report_generator import (
    _retrieve_local_verified_knowledge,
    generate_research_report,
)
from apps.schemes.models import Authority, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument
from apps.startups.models import StartupProfile

User = get_user_model()


def successful_llm_payload(*, sources=None):
    return {
        "startup_summary": "Grounded summary",
        "historical_peers": [],
        "current_competitors": [],
        "recent_market_developments": [],
        "government_schemes": [],
        "risks": [],
        "market_gaps": [],
        "capital_scenarios": "Validate costs.",
        "recommended_next_actions": [],
        "sources": sources or [],
        "confidence_score": 0.7,
    }


class SuccessfulLLM:
    model_name = "test-model"

    def __init__(self, *, sources=None):
        self.sources = sources

    def generate(self, **kwargs):
        return SimpleNamespace(
            payload=successful_llm_payload(sources=self.sources),
            model_name=self.model_name,
        )


@pytest.mark.django_db
def test_research_report_marks_unavailable_live_search_partial(
    monkeypatch,
    settings,
):
    settings.WEB_SEARCH_ENABLED = False
    user = User.objects.create_user(username="researcher", password="password123")
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="HealthWrist",
        stage="idea",
        state="Karnataka",
        sectors=["Healthcare"],
    )

    req = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="What is the latest market situation for smart health wristbands?",
    )
    monkeypatch.setattr(
        "apps.research.services.report_generator.get_startup_advisor_llm_provider",
        lambda: SuccessfulLLM(
            sources=["internal://companies/invented-company"]
        ),
    )

    report = generate_research_report(str(req.id))

    assert isinstance(report, StartupResearchReport)
    assert report.startup_profile == profile
    req.refresh_from_db()
    assert req.status == ResearchRequest.Status.PARTIAL
    assert req.requires_live_search is True
    assert report.live_search_date is None
    assert report.report["research_metadata"]["live_search_status"] == "unavailable"
    assert report.report["research_metadata"]["llm_status"] == "generated"
    assert "internal://companies/invented-company" not in report.report["sources"]
    assert req.search_queries.filter(
        status=ResearchSearchQuery.Status.FAILED,
    ).count() == 3


@pytest.mark.django_db
def test_local_rag_retrieves_verified_company_and_scheme():
    user = User.objects.create_user(
        username="local-rag-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Care Platform",
        stage=StartupProfile.Stage.MVP,
        sectors=["Healthcare"],
    )
    Company.objects.create(
        canonical_name="Verified Health Peer",
        industry="Healthcare SaaS",
        business_model="subscription",
        country="India",
        operating_status=Company.OperatingStatus.ACTIVE,
        verification_status=Company.VerificationStatus.VERIFIED,
    )
    Company.objects.create(
        canonical_name="Unverified Health Peer",
        industry="Healthcare SaaS",
        business_model="subscription",
        country="India",
        verification_status=Company.VerificationStatus.UNVERIFIED,
    )
    source = Source.objects.create(
        name="Research scheme source",
        official_domain="research-scheme.gov.in",
        listing_url="https://research-scheme.gov.in/",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://research-scheme.gov.in/scheme.pdf",
        mime_type="application/pdf",
        content_hash="research-scheme-document",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )
    authority = Authority.objects.create(
        name="Research Scheme Authority",
        ministry="Ministry of Health",
    )
    scheme = Scheme.objects.create(
        canonical_name="Verified Health Innovation Scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=document,
        captured_at=timezone.now(),
        content_hash="research-scheme-version",
        official_url="https://research-scheme.gov.in/apply/",
        description="Supports verified healthcare startups.",
        eligible_sectors=["Healthcare"],
        eligible_stages=["mvp"],
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
    )
    scheme.current_version = version
    scheme.save(update_fields=["current_version"])

    evidence = _retrieve_local_verified_knowledge(profile)

    titles = {item["title"] for item in evidence}
    assert "Historical Peer: Verified Health Peer" in titles
    assert "Historical Peer: Unverified Health Peer" not in titles
    assert "Official Scheme: Verified Health Innovation Scheme" in titles
    scheme_evidence = next(
        item for item in evidence if item["title"].startswith("Official Scheme")
    )
    assert scheme_evidence["url"] == version.official_url
    assert "Ministry of Health" in scheme_evidence["content_excerpt"]


@pytest.mark.django_db
def test_database_constraint_allows_only_one_active_job_per_profile():
    user = User.objects.create_user(
        username="concurrent-researcher",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Concurrency Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="First active research request",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ResearchRequest.objects.create(
            startup_profile=profile,
            requested_by=user,
            question="Concurrent active research request",
        )


@pytest.mark.django_db
def test_research_request_api(client, monkeypatch):
    user = User.objects.create_user(username="founder_user", password="password123")
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="MedTech",
        stage="mvp",
    )

    client.force_login(user)
    monkeypatch.setattr(
        "apps.research.views.generate_research_report_task.delay",
        lambda *args, **kwargs: SimpleNamespace(id="research-task-123"),
    )

    # Create request
    response = client.post(
        "/api/v1/research/requests/",
        {
            "startup_profile_id": str(profile.id),
            "question": "What are current competitors for health wearables in India?",
        },
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["job"]["id"]

    # Detail request
    detail_res = client.get(f"/api/v1/research/requests/{job_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.data["question"] == "What are current competitors for health wearables in India?"


@pytest.mark.django_db
def test_founder_cannot_read_another_founders_report(client):
    owner = User.objects.create_user(
        username="research-owner",
        email="research-owner@example.com",
        password="password123",
    )
    outsider = User.objects.create_user(
        username="research-outsider",
        email="research-outsider@example.com",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=owner,
        startup_name="Private Research Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=owner,
        question="Private historical research question",
        status=ResearchRequest.Status.SUCCEEDED,
    )
    report = StartupResearchReport.objects.create(
        startup_profile=profile,
        research_request=request,
        model_name="test-model",
        report=successful_llm_payload(),
    )
    client.force_login(outsider)

    response = client.get(f"/api/v1/research/reports/{report.id}/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
