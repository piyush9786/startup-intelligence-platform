from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.sources.models import CrawlRun, Source, SourceDocument
from apps.sources.services.security import validate_collection_url
from apps.sources.services.storage import upload_bytes


class CollectionError(RuntimeError):
    """Raised when a source document cannot be collected safely."""


@dataclass(frozen=True)
class DownloadedDocument:
    requested_url: str
    final_url: str
    content: bytes
    mime_type: str
    status_code: int
    headers: dict[str, str]
    warnings: list[str]


@dataclass(frozen=True)
class CollectionResult:
    document: SourceDocument
    run: CrawlRun
    created: bool
    unchanged: bool


def _content_type(headers: httpx.Headers, url: str) -> str:
    value = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if value:
        return value
    guessed, _ = mimetypes.guess_type(url)
    return guessed or "application/octet-stream"


def _extension(mime_type: str, url: str) -> str:
    mapping = {
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "application/pdf": ".pdf",
        "application/json": ".json",
        "text/plain": ".txt",
        "text/csv": ".csv",
    }
    if mime_type in mapping:
        return mapping[mime_type]
    suffix = PurePosixPath(urlsplit(url).path).suffix.lower()
    return suffix[:12] if suffix else ".bin"


def _validate_mime_type(mime_type: str, url: str) -> None:
    allowed = {
        "text/html",
        "application/xhtml+xml",
        "application/pdf",
        "application/json",
        "text/plain",
        "text/csv",
    }
    if mime_type in allowed:
        return
    if mime_type == "application/octet-stream" and urlsplit(url).path.lower().endswith(".pdf"):
        return
    raise CollectionError(f"Unsupported content type: {mime_type}")


def _extract_title(content: bytes, mime_type: str) -> str:
    if mime_type not in {"text/html", "application/xhtml+xml"}:
        return ""
    soup = BeautifulSoup(content, "html.parser")
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())[:500]
    heading = soup.find("h1")
    if heading:
        return " ".join(heading.get_text(" ", strip=True).split())[:500]
    return ""


def _check_robots(
    *,
    client: httpx.Client,
    source: Source,
    url: str,
    warnings: list[str],
) -> None:
    if not source.respect_robots_txt:
        return

    parsed = urlsplit(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    validate_collection_url(robots_url, source)

    try:
        response = client.get(robots_url)
    except httpx.HTTPError as exc:
        warnings.append(f"robots.txt could not be checked: {exc}")
        return

    if response.status_code in {401, 403}:
        raise CollectionError("robots.txt access was denied by the source.")
    if response.status_code != 200:
        warnings.append(f"robots.txt returned HTTP {response.status_code}")
        return

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(settings.COLLECTOR_USER_AGENT, url):
        raise CollectionError("Collection is disallowed by robots.txt.")


def download_document(source: Source, requested_url: str) -> DownloadedDocument:
    validate_collection_url(requested_url, source)
    timeout = httpx.Timeout(float(source.request_timeout_seconds))
    headers = {
        "User-Agent": settings.COLLECTOR_USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/pdf,application/json,text/plain,*/*;q=0.2"
        ),
    }
    warnings: list[str] = []

    with httpx.Client(
        timeout=timeout,
        headers=headers,
        follow_redirects=False,
        verify=True,
    ) as client:
        _check_robots(
            client=client,
            source=source,
            url=requested_url,
            warnings=warnings,
        )

        current_url = requested_url
        for _ in range(settings.COLLECTOR_MAX_REDIRECTS + 1):
            validate_collection_url(current_url, source)
            with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise CollectionError("Redirect response did not include Location.")
                    current_url = urljoin(current_url, location)
                    continue

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise CollectionError(f"Source returned HTTP {response.status_code}") from exc

                declared_length = response.headers.get("content-length")
                if declared_length and int(declared_length) > source.max_document_bytes:
                    raise CollectionError(
                        "Document exceeds the configured maximum size before download."
                    )

                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > source.max_document_bytes:
                        raise CollectionError(
                            "Document exceeded the configured maximum size during download."
                        )
                    chunks.append(chunk)

                mime_type = _content_type(response.headers, current_url)
                _validate_mime_type(mime_type, current_url)
                return DownloadedDocument(
                    requested_url=requested_url,
                    final_url=str(response.url),
                    content=b"".join(chunks),
                    mime_type=mime_type,
                    status_code=response.status_code,
                    headers={key.lower(): value for key, value in response.headers.items()},
                    warnings=warnings,
                )

    raise CollectionError(f"Too many redirects; maximum is {settings.COLLECTOR_MAX_REDIRECTS}.")


def collect_source(
    source: Source,
    *,
    url: str | None = None,
    trigger: str = CrawlRun.Trigger.MANUAL,
) -> CollectionResult:
    requested_url = url or source.listing_url
    run = CrawlRun.objects.create(
        source=source,
        trigger=trigger,
        requested_url=requested_url,
        status=CrawlRun.Status.RUNNING,
        started_at=timezone.now(),
    )

    try:
        downloaded = download_document(source, requested_url)
        content_hash = hashlib.sha256(downloaded.content).hexdigest()
        retrieved_at = timezone.now()

        existing = SourceDocument.objects.filter(
            source_url=requested_url,
            content_hash=content_hash,
            is_current=True,
        ).first()
        if existing:
            source.last_checked_at = retrieved_at
            source.save(update_fields=["last_checked_at", "updated_at"])
            run.status = CrawlRun.Status.SUCCEEDED
            run.documents_unchanged = 1
            run.finished_at = retrieved_at
            run.metadata = {"warnings": downloaded.warnings}
            run.save(
                update_fields=[
                    "status",
                    "documents_unchanged",
                    "finished_at",
                    "metadata",
                    "updated_at",
                ]
            )
            return CollectionResult(
                document=existing,
                run=run,
                created=False,
                unchanged=True,
            )

        extension = _extension(downloaded.mime_type, downloaded.final_url)
        date_path = datetime.now(UTC).strftime("%Y/%m/%d")
        object_key = f"sources/{source.id}/{date_path}/{content_hash[:2]}/{content_hash}{extension}"
        upload_bytes(
            object_key=object_key,
            content=downloaded.content,
            content_type=downloaded.mime_type,
        )

        with transaction.atomic():
            current = (
                SourceDocument.objects.select_for_update()
                .filter(source_url=requested_url, is_current=True)
                .order_by("-version_number")
                .first()
            )
            latest_version = (
                SourceDocument.objects.filter(source_url=requested_url).aggregate(
                    maximum=Max("version_number")
                )["maximum"]
                or 0
            )
            if current:
                current.is_current = False
                current.save(update_fields=["is_current", "updated_at"])

            document = SourceDocument.objects.create(
                source=source,
                crawl_run=run,
                supersedes=current,
                source_url=requested_url,
                final_url=downloaded.final_url,
                title=_extract_title(downloaded.content, downloaded.mime_type),
                mime_type=downloaded.mime_type,
                storage_key=object_key,
                content_hash=content_hash,
                version_number=latest_version + 1,
                is_current=True,
                retrieved_at=retrieved_at,
                http_status=downloaded.status_code,
                etag=downloaded.headers.get("etag", "")[:500],
                last_modified=downloaded.headers.get("last-modified", "")[:500],
                content_length=len(downloaded.content),
                response_headers=downloaded.headers,
                metadata={"warnings": downloaded.warnings},
            )

        source.last_checked_at = retrieved_at
        source.save(update_fields=["last_checked_at", "updated_at"])
        run.status = CrawlRun.Status.SUCCEEDED
        run.documents_created = 1
        run.finished_at = retrieved_at
        run.metadata = {"warnings": downloaded.warnings}
        run.save(
            update_fields=[
                "status",
                "documents_created",
                "finished_at",
                "metadata",
                "updated_at",
            ]
        )
        return CollectionResult(
            document=document,
            run=run,
            created=True,
            unchanged=False,
        )
    except Exception as exc:
        finished_at = timezone.now()
        run.status = CrawlRun.Status.FAILED
        run.error_count = 1
        run.error_message = str(exc)[:4000]
        run.finished_at = finished_at
        run.save(
            update_fields=[
                "status",
                "error_count",
                "error_message",
                "finished_at",
                "updated_at",
            ]
        )
        source.last_checked_at = finished_at
        source.save(update_fields=["last_checked_at", "updated_at"])
        if isinstance(exc, CollectionError):
            raise
        raise CollectionError(str(exc)) from exc
