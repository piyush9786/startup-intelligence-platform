from apps.documents.services.chunker import build_chunks
from apps.documents.services.extractors import ExtractedSection


def test_chunking_is_deterministic_and_respects_limit():
    section = ExtractedSection(
        heading="Eligibility",
        text=" ".join(["startup eligibility condition"] * 80),
    )
    chunks = build_chunks(
        [section],
        max_chars=300,
        overlap_chars=40,
        max_chunks=20,
    )

    assert len(chunks) > 1
    assert [item.chunk_index for item in chunks] == list(range(len(chunks)))
    assert all(len(item.text) <= 300 for item in chunks)
    assert all(item.heading == "Eligibility" for item in chunks)
    assert all(item.text_hash for item in chunks)
