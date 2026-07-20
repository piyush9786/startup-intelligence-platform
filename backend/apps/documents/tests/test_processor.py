from __future__ import annotations

import pytest
from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.documents.services import processor
from apps.documents.services.processor import process_document
from apps.sources.models import Source, SourceDocument


@pytest.mark.django_db
def test_processing_creates_chunks_and_is_idempotent(monkeypatch):
    source = Source.objects.create(
        name="Example Authority",
        category="test",
        official_domain="example.com",
        listing_url="https://example.com/schemes",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
        respect_robots_txt=False,
    )
    document = SourceDocument.objects.create(
        source=source,
        source_url="https://example.com/schemes",
        final_url="https://example.com/schemes",
        title="Example",
        mime_type="text/html",
        storage_key="sources/example.html",
        content_hash="a" * 64,
        retrieved_at=timezone.now(),
        content_length=100,
    )

    monkeypatch.setattr(
        processor,
        "download_bytes",
        lambda _key: b"<main><h1>Grant</h1><p>Support for startups.</p></main>",
    )
    monkeypatch.setattr(
        processor,
        "upload_bytes",
        lambda **kwargs: kwargs["object_key"],
    )

    first = process_document(document)
    assert first.unchanged is False
    assert first.extraction.status == DocumentExtraction.Status.SUCCEEDED
    assert first.extraction.chunk_count == 1
    assert DocumentChunk.objects.count() == 1

    second = process_document(document)
    assert second.unchanged is True
    assert DocumentExtraction.objects.count() == 1
    assert DocumentChunk.objects.count() == 1

    document.refresh_from_db()
    assert document.status == SourceDocument.Status.EXTRACTED
