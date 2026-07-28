from __future__ import annotations

import pytest
from django.utils import timezone

from apps.sources.models import Source, SourceDocument
from apps.sources.services import collector
from apps.sources.services.collector import DownloadedDocument, collect_source


@pytest.fixture
def source(db):
    return Source.objects.create(
        name="Example Authority",
        category="test",
        official_domain="example.com",
        listing_url="https://example.com/schemes",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
        respect_robots_txt=False,
    )


@pytest.mark.django_db
def test_collection_creates_versions_and_detects_unchanged(
    source,
    monkeypatch,
):
    payloads = [b"<html><title>Version One</title></html>"]

    def fake_download(_source, requested_url):
        return DownloadedDocument(
            requested_url=requested_url,
            final_url=requested_url,
            content=payloads[-1],
            mime_type="text/html",
            status_code=200,
            headers={"etag": '"abc"'},
            warnings=[],
        )

    monkeypatch.setattr(collector, "download_document", fake_download)
    monkeypatch.setattr(
        collector,
        "upload_bytes",
        lambda **kwargs: kwargs["object_key"],
    )

    first = collect_source(source)
    assert first.created is True
    assert first.document.version_number == 1
    assert first.document.is_current is True
    assert first.document.title == "Version One"

    second = collect_source(source)
    assert second.unchanged is True
    assert SourceDocument.objects.count() == 1

    payloads.append(b"<html><title>Version Two</title></html>")
    third = collect_source(source)
    assert third.created is True
    assert third.document.version_number == 2
    assert third.document.supersedes == first.document

    first.document.refresh_from_db()
    assert first.document.is_current is False
    assert third.document.is_current is True
    assert SourceDocument.objects.count() == 2
    assert third.run.finished_at <= timezone.now()
