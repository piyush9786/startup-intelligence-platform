from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .extractors import ExtractedSection
from .normalizer import normalize_text, token_estimate


@dataclass(frozen=True)
class ChunkPayload:
    chunk_index: int
    heading: str
    page_number: int | None
    text: str
    text_hash: str
    character_start: int
    character_end: int
    token_estimate: int
    metadata: dict[str, Any]


def _best_boundary(text: str, start: int, target_end: int) -> int:
    if target_end >= len(text):
        return len(text)

    lower_bound = start + int((target_end - start) * 0.6)
    candidates = [
        text.rfind("\n\n", lower_bound, target_end),
        text.rfind(". ", lower_bound, target_end),
        text.rfind("\n", lower_bound, target_end),
        text.rfind(" ", lower_bound, target_end),
    ]
    boundary = max(candidates)
    if boundary <= start:
        return target_end
    if text[boundary : boundary + 2] in {"\n\n", ". "}:
        return boundary + 1
    return boundary


def split_section(
    section: ExtractedSection,
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[tuple[str, int, int]]:
    text = normalize_text(section.text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [(text, 0, len(text))]

    chunks: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        target_end = min(len(text), start + max_chars)
        end = _best_boundary(text, start, target_end)
        if end <= start:
            end = target_end
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((chunk_text, start, end))
        if end >= len(text):
            break
        next_start = max(0, end - overlap_chars)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        start = next_start if next_start < end else end
    return chunks


def build_chunks(
    sections: list[ExtractedSection],
    *,
    max_chars: int,
    overlap_chars: int,
    max_chunks: int,
) -> list[ChunkPayload]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars - 1")

    payloads: list[ChunkPayload] = []
    document_offset = 0
    for section in sections:
        for text, local_start, local_end in split_section(
            section,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ):
            if len(payloads) >= max_chunks:
                raise ValueError(f"Document exceeds the configured limit of {max_chunks} chunks.")
            payloads.append(
                ChunkPayload(
                    chunk_index=len(payloads),
                    heading=section.heading[:500],
                    page_number=section.page_number,
                    text=text,
                    text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    character_start=document_offset + local_start,
                    character_end=document_offset + local_end,
                    token_estimate=token_estimate(text),
                    metadata=section.metadata or {},
                )
            )
        document_offset += len(section.text) + 2
    return payloads
