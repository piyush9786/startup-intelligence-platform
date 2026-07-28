from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.discovery.models import DocumentQualityAssessment
from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.knowledge.models import EmbeddingRun
from apps.knowledge.services.embeddings import EmbeddingBatch
from apps.knowledge.services.vector_search import (
    index_document_extraction,
    search_document_chunks,
)
from apps.sources.models import Source, SourceDocument

pytestmark = pytest.mark.django_db


class FakeEmbeddingProvider:
    provider_name = "fake"

    def __init__(self):
        self.model_name = "fake-embedding"
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return EmbeddingBatch(
            vectors=[
                [float(index + 1), 0.25, 0.5]
                for index, _text in enumerate(texts)
            ],
            model_name=self.model_name,
            dimension=3,
        )


class FakeQdrantClient:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.upserted = []
        self.query_response = SimpleNamespace(points=[])

    def collection_exists(self, collection_name):
        return False

    def create_collection(self, **kwargs):
        self.created.append(kwargs)

    def delete(self, **kwargs):
        self.deleted.append(kwargs)

    def upsert(self, **kwargs):
        self.upserted.append(kwargs)

    def query_points(self, **kwargs):
        self.query_kwargs = kwargs
        return self.query_response


def make_extraction():
    source = Source.objects.create(
        name="Official startup source",
        category="government",
        official_domain="example.gov.in",
        allowed_domains=["example.gov.in"],
        listing_url="https://example.gov.in/schemes",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://example.gov.in/scheme.pdf",
        final_url="https://example.gov.in/scheme.pdf",
        title="Example Scheme",
        mime_type="application/pdf",
        storage_key="raw/example.pdf",
        content_hash="a" * 64,
        retrieved_at=datetime.now(UTC),
        status=SourceDocument.Status.EXTRACTED,
    )
    extraction = DocumentExtraction.objects.create(
        source_document=document,
        extractor_version="v2",
        status=DocumentExtraction.Status.SUCCEEDED,
        detected_title="Example Scheme Guidelines",
        text_hash="b" * 64,
        chunk_count=2,
        word_count=20,
        character_count=100,
        finished_at=timezone.now(),
    )
    DocumentChunk.objects.create(
        extraction=extraction,
        chunk_index=0,
        heading="Eligibility",
        page_number=1,
        text="Eligible startups must be DPIIT recognised.",
        text_hash="c" * 64,
        token_estimate=10,
    )
    DocumentChunk.objects.create(
        extraction=extraction,
        chunk_index=1,
        heading="Benefits",
        page_number=2,
        text="The programme provides grant support.",
        text_hash="d" * 64,
        token_estimate=10,
    )
    DocumentQualityAssessment.objects.create(
        extraction=extraction,
        page_type="guideline_pdf",
        score=80,
        usable_for_discovery=True,
        usable_for_rag=True,
        usable_for_structured_extraction=True,
    )
    return extraction


def test_index_extraction_embeds_chunks_and_tracks_run(settings):
    settings.STARTUP_ADVISOR_EMBEDDING_MODEL = "fake-embedding"
    settings.STARTUP_ADVISOR_EMBEDDING_VERSION = "fake-v1"
    settings.STARTUP_ADVISOR_QDRANT_COLLECTION = "test-chunks"
    settings.STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE = 16

    extraction = make_extraction()
    provider = FakeEmbeddingProvider()
    client = FakeQdrantClient()

    result = index_document_extraction(
        extraction,
        provider=provider,
        client=client,
    )

    assert result.embedded_count == 2
    assert result.run.status == EmbeddingRun.Status.SUCCEEDED
    assert result.run.vector_size == 3
    assert result.run.chunk_count == 2
    assert client.created[0]["collection_name"] == "test-chunks"
    assert len(client.upserted[0]["points"]) == 2
    payload = client.upserted[0]["points"][0].payload
    assert payload["source_url"] == "https://example.gov.in/scheme.pdf"
    assert payload["usable_for_rag"] is True


def test_search_returns_prompt_ready_evidence(settings):
    settings.STARTUP_ADVISOR_QDRANT_COLLECTION = "test-chunks"
    settings.STARTUP_ADVISOR_RAG_TOP_K = 4
    settings.STARTUP_ADVISOR_RAG_MIN_SCORE = 0.2

    provider = FakeEmbeddingProvider()
    client = FakeQdrantClient()
    client.query_response = SimpleNamespace(
        points=[
            SimpleNamespace(
                score=0.91,
                payload={
                    "chunk_id": "80c92c34-b78e-45b8-af0a-1052a9a81ed0",
                    "text": "Eligible startups must be DPIIT recognised.",
                    "source_url": "https://example.gov.in/scheme.pdf",
                    "title": "Example Scheme",
                    "page_number": 1,
                    "heading": "Eligibility",
                    "extraction_id": "11111111-1111-1111-1111-111111111111",
                    "document_id": "22222222-2222-2222-2222-222222222222",
                },
            )
        ]
    )

    results = search_document_chunks(
        "DPIIT recognition eligibility",
        provider=provider,
        client=client,
    )

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.91)
    assert results[0].as_prompt_document()["page_number"] == 1
    assert client.query_kwargs["limit"] == 4
