from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Any

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .normalizer import normalize_text


class ExtractionError(RuntimeError):
    """Raised when raw bytes cannot be converted into usable text."""


@dataclass(frozen=True)
class ExtractedSection:
    text: str
    heading: str = ""
    page_number: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ExtractionPayload:
    title: str
    sections: list[ExtractedSection]
    page_count: int
    metadata: dict[str, Any]

    @property
    def combined_text(self) -> str:
        values: list[str] = []
        for section in self.sections:
            if section.heading:
                values.append(section.heading)
            values.append(section.text)
        return normalize_text("\n\n".join(values))


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def extract_html(content: bytes) -> ExtractionPayload:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "noscript", "template", "svg", "canvas"]):
        element.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string)[:500]

    root = soup.find("main") or soup.find("article") or soup.body or soup
    sections: list[ExtractedSection] = []
    current_heading = ""
    buffered: list[str] = []

    def flush() -> None:
        nonlocal buffered
        text = normalize_text("\n".join(buffered))
        if text:
            sections.append(
                ExtractedSection(
                    text=text,
                    heading=current_heading,
                    metadata={"source": "html"},
                )
            )
        buffered = []

    for element in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr"]):
        value = normalize_text(element.get_text(" ", strip=True))
        if not value:
            continue
        if element.name and element.name.startswith("h"):
            flush()
            current_heading = value[:500]
            if not title and element.name == "h1":
                title = value[:500]
        elif not buffered or buffered[-1] != value:
            buffered.append(value)
    flush()

    if not sections:
        fallback = normalize_text(root.get_text("\n", strip=True))
        if fallback:
            sections = [ExtractedSection(text=fallback)]

    if not sections:
        raise ExtractionError("HTML document did not contain extractable text.")

    return ExtractionPayload(
        title=title,
        sections=sections,
        page_count=0,
        metadata={"format": "html"},
    )


def extract_pdf(content: bytes) -> ExtractionPayload:
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"PDF could not be opened: {exc}") from exc

    title = ""
    if reader.metadata and reader.metadata.title:
        title = normalize_text(str(reader.metadata.title))[:500]

    sections: list[ExtractedSection] = []
    empty_pages: list[int] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = normalize_text(page.extract_text() or "")
        except Exception as exc:
            empty_pages.append(page_number)
            text = ""
            page_error = str(exc)
        else:
            page_error = ""

        if text:
            metadata: dict[str, Any] = {"source": "pdf"}
            if page_error:
                metadata["warning"] = page_error
            sections.append(
                ExtractedSection(
                    text=text,
                    heading=f"Page {page_number}",
                    page_number=page_number,
                    metadata=metadata,
                )
            )
        else:
            empty_pages.append(page_number)

    if not sections:
        raise ExtractionError("PDF contained no extractable text. It may require OCR.")

    return ExtractionPayload(
        title=title,
        sections=sections,
        page_count=len(reader.pages),
        metadata={
            "format": "pdf",
            "empty_pages": sorted(set(empty_pages)),
        },
    )


def extract_json(content: bytes) -> ExtractionPayload:
    try:
        payload = json.loads(_decode_text(content))
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"JSON parsing failed: {exc}") from exc

    text = normalize_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return ExtractionPayload(
        title="",
        sections=[ExtractedSection(text=text)],
        page_count=0,
        metadata={"format": "json"},
    )


def extract_csv(content: bytes) -> ExtractionPayload:
    decoded = _decode_text(content)
    reader = csv.reader(StringIO(decoded))
    lines: list[str] = []
    for row in reader:
        values = [normalize_text(value) for value in row]
        lines.append(" | ".join(values))
    text = normalize_text("\n".join(lines))
    if not text:
        raise ExtractionError("CSV document did not contain extractable text.")
    return ExtractionPayload(
        title="",
        sections=[ExtractedSection(text=text)],
        page_count=0,
        metadata={"format": "csv"},
    )


def extract_plain_text(content: bytes) -> ExtractionPayload:
    text = normalize_text(_decode_text(content))
    if not text:
        raise ExtractionError("Text document was empty.")
    return ExtractionPayload(
        title="",
        sections=[ExtractedSection(text=text)],
        page_count=0,
        metadata={"format": "text"},
    )


def extract_document(content: bytes, mime_type: str) -> ExtractionPayload:
    normalized_mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if normalized_mime in {"text/html", "application/xhtml+xml"}:
        return extract_html(content)
    if normalized_mime in {"application/pdf", "application/octet-stream"}:
        return extract_pdf(content)
    if normalized_mime == "application/json":
        return extract_json(content)
    if normalized_mime == "text/csv":
        return extract_csv(content)
    if normalized_mime == "text/plain":
        return extract_plain_text(content)
    raise ExtractionError(f"Unsupported extraction MIME type: {normalized_mime}")
