"""Reliability tests for research orchestration and delivery."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from billiard.exceptions import SoftTimeLimitExceeded
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from jsonschema import Draft202012Validator
from rest_framework import status

from apps.research.models import (
    ResearchEvidence,
    ResearchRequest,
    ResearchSearchQuery,
)
from apps.research.orchestration.dependencies import (
    ResearchDependencies,
)
from apps.research.orchestration.state import ResearchState
from apps.research.orchestration.steps import (
    finalize_research_metadata,
    retrieve_live_evidence,
    retrieve_vector_evidence,
)
from apps.research.services.report_schema import (
    FINAL_RESEARCH_REPORT_SCHEMA,
)
from apps.research.services.vector_retrieval import (
    _generate_query_embedding,
    retrieve_startup_vector_evidence,
)
from apps.research.tasks import generate_research_report_task
from apps.startups.models import StartupProfile

User = get_user_model()


@pytest.fixture
def research_request():
    user = User.objects.create_user(
        username="research-reliability-founder",
        password="password123",
    )
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Reliable Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="What changed in our market recently?",
    )
    return user, profile, request


@pytest.mark.django_db
def test_final_persisted_report_schema_accepts_metadata(
    research_request,
):
    _, _, request = research_request
    state = ResearchState.from_request(request)
    state.local_evidence = [{"url": "internal://profile"}]
    state.live_search_status = "not_required"
    state.vector_retrieval_status = "disabled"
    state.llm_status = "generated"
    state.report_data = {
        "startup_summary": "Grounded summary",
        "historical_peers": [],
        "current_competitors": [],
        "recent_market_developments": [],
        "government_schemes": [],
        "compliance_requirements": [],
        "funding_opportunities": [],
        "loan_options": [],
        "risks": [],
        "market_gaps": [],
        "capital_scenarios": "Validate costs.",
        "recommended_next_actions": [],
        "sources": ["internal://profile"],
        "confidence_score": 0.8,
    }

    final_state = finalize_research_metadata(
        state,
        ResearchDependencies(),
    )

    Draft202012Validator(
        FINAL_RESEARCH_REPORT_SCHEMA,
    ).validate(final_state.report_data)
    assert "research_metadata" in final_state.report_data


@pytest.mark.django_db
def test_search_redelivery_updates_one_query_row(
    research_request,
    settings,
):
    _, _, request = research_request
    settings.WEB_SEARCH_PROVIDER = "tavily"
    state = ResearchState.from_request(request)
    state.requires_live_search = True
    state.queries = ["reliable startup market India"]
    dependencies = ResearchDependencies(
        web_search=lambda *args, **kwargs: [],
        extract_evidence=lambda *args, **kwargs: [],
    )

    retrieve_live_evidence(state, dependencies)
    retrieve_live_evidence(state, dependencies)

    assert ResearchSearchQuery.objects.filter(
        research_request=request,
    ).count() == 1


@pytest.mark.django_db
def test_evidence_constraint_blocks_duplicate_hash(
    research_request,
):
    _, _, request = research_request
    values = {
        "research_request": request,
        "title": "Evidence",
        "url": "https://example.com/evidence",
        "content_excerpt": "Verified evidence",
        "content_hash": "a" * 64,
    }
    ResearchEvidence.objects.create(**values)

    with pytest.raises(IntegrityError), transaction.atomic():
        ResearchEvidence.objects.create(**values)


@pytest.mark.django_db
def test_soft_timeout_marks_request_failed(
    research_request,
    monkeypatch,
):
    _, _, request = research_request

    def raise_timeout(*args, **kwargs):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(
        "apps.research.tasks.generate_research_report",
        raise_timeout,
    )

    with pytest.raises(SoftTimeLimitExceeded):
        generate_research_report_task.run(str(request.id))

    request.refresh_from_db()
    assert request.status == ResearchRequest.Status.FAILED
    assert request.error_code == "task_timeout"
    assert request.completed_at is not None


@pytest.mark.django_db
def test_dispatch_failure_returns_503(
    client,
    research_request,
    monkeypatch,
):
    user, profile, existing_request = research_request
    existing_request.status = ResearchRequest.Status.FAILED
    existing_request.save(update_fields=["status", "updated_at"])
    client.force_login(user)

    monkeypatch.setattr(
        "apps.research.views.generate_research_report_task.delay",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("broker unavailable")
        ),
    )

    response = client.post(
        "/api/v1/research/requests/",
        {
            "startup_profile_id": str(profile.id),
            "question": "Give me a current market assessment.",
        },
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    job = ResearchRequest.objects.get(id=response.data["job"]["id"])
    assert job.status == ResearchRequest.Status.FAILED
    assert job.error_code == "dispatch_failed"
    assert job.completed_at is not None


@pytest.mark.django_db
def test_vector_step_is_owner_scoped_and_fail_soft(
    research_request,
    settings,
):
    _, profile, request = research_request
    settings.STARTUP_ADVISOR_RAG_ENABLED = False
    settings.RESEARCH_VECTOR_RAG_ENABLED = True
    settings.RESEARCH_VECTOR_RAG_TOP_K = 4
    captured = {}

    def retrieve(**kwargs):
        captured.update(kwargs)
        return []

    state = ResearchState.from_request(request)
    retrieve_vector_evidence(
        state,
        ResearchDependencies(
            retrieve_vector_evidence=retrieve,
        ),
    )

    assert captured["startup_profile_id"] == str(profile.id)
    assert captured["query"] == request.question
    assert captured["top_k"] == 4
    assert state.vector_retrieval_status == "empty"


@pytest.mark.django_db
def test_vector_step_is_independent_of_advisor_rag_setting(
    research_request,
    settings,
):
    _, _, request = research_request
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    settings.RESEARCH_VECTOR_RAG_ENABLED = False
    called = False

    def retrieve(**kwargs):
        nonlocal called
        called = True
        return []

    state = ResearchState.from_request(request)
    retrieve_vector_evidence(
        state,
        ResearchDependencies(
            retrieve_vector_evidence=retrieve,
        ),
    )

    assert called is False
    assert state.vector_retrieval_status == "disabled"


def test_qdrant_retrieval_uses_profile_filter(
    settings,
    monkeypatch,
):
    settings.RESEARCH_VECTOR_QDRANT_COLLECTION = "research-test-collection"
    settings.RESEARCH_VECTOR_QDRANT_PROFILE_FIELD = (
        "startup_profile_id"
    )
    settings.RESEARCH_VECTOR_RAG_TOP_K = 6
    settings.RESEARCH_VECTOR_RAG_MIN_SCORE = 0.35
    captured = {}

    class FakeClient:
        def query_points(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id="point-1",
                        score=0.91,
                        payload={
                            "startup_profile_id": "profile-1",
                            "title": "Pitch deck",
                            "content": "Verified founder document.",
                            "document_id": "document-1",
                            "chunk_index": 2,
                        },
                    ),
                    SimpleNamespace(
                        id="point-other-owner",
                        score=0.99,
                        payload={
                            "startup_profile_id": "profile-2",
                            "title": "Another founder's document",
                            "content": "Must never enter this context.",
                        },
                    ),
                ]
            )

        def close(self):
            return None

    monkeypatch.setattr(
        "apps.research.services.vector_retrieval._generate_query_embedding",
        lambda query: [0.1, 0.2],
    )
    monkeypatch.setattr(
        "apps.research.services.vector_retrieval._build_qdrant_client",
        FakeClient,
    )

    evidence = retrieve_startup_vector_evidence(
        startup_profile_id="profile-1",
        query="What do our documents say?",
    )

    field_condition = captured["query_filter"].must[0]
    assert captured["collection_name"] == "research-test-collection"
    assert captured["limit"] == 6
    assert field_condition.key == "startup_profile_id"
    assert field_condition.match.value == "profile-1"
    assert evidence[0]["verification_status"] == "verified_internal"
    assert evidence[0]["confidence_score"] == pytest.approx(0.91)
    assert len(evidence) == 1


def test_ollama_embedding_uses_current_embed_response(
    settings,
    monkeypatch,
):
    settings.OLLAMA_BASE_URL = "http://ollama:11434"
    settings.STARTUP_ADVISOR_EMBEDDING_MODEL = "embeddinggemma"
    settings.STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS = 30
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "embeddinggemma",
                "embeddings": [[0.1, 0.2, 0.3]],
            }

    class FakeHttpClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, *, json):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(
        "apps.research.services.vector_retrieval.httpx.Client",
        FakeHttpClient,
    )

    embedding = _generate_query_embedding("founder evidence")

    assert embedding == [0.1, 0.2, 0.3]
    assert captured["url"] == "http://ollama:11434/api/embed"
    assert captured["payload"] == {
        "model": "embeddinggemma",
        "input": "founder evidence",
        "truncate": True,
    }
