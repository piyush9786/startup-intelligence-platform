"""
Model 7 — TF-IDF + Cosine Similarity: Hybrid Sparse Search Index

Builds a TF-IDF matrix over all scheme descriptions, objectives, and
eligibility rule evidence texts. Used as the sparse retrieval leg of the
3-stage Hybrid RAG pipeline alongside Qdrant's dense vector search.

Merging dense + sparse results via Reciprocal Rank Fusion (RRF) dramatically
improves recall for queries that contain specific keyword terms (e.g., exact
scheme names, sector names, or registration identifiers like "DPIIT").
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from apps.ml_engine.services.model_store import load_model, next_version, save_model

MODEL_TYPE = "tfidf"
MODEL_NAME = "tfidf_hybrid_search"


def build_tfidf_index(scheme_corpus: list[dict]) -> dict:
    """
    Build and persist a TF-IDF index over scheme text corpus.

    Args:
        scheme_corpus: List of dicts with keys:
            - "scheme_version_id": str
            - "text": combined description + objective + eligibility evidence

    Returns:
        dict with registry entry and corpus size.
    """
    texts = [item["text"] for item in scheme_corpus]
    ids = [item["scheme_version_id"] for item in scheme_corpus]

    vectorizer = TfidfVectorizer(
        max_features=10_000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    bundle = {
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "scheme_version_ids": ids,
    }

    version = next_version(MODEL_TYPE)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=bundle,
        version=version,
        training_sample_count=len(texts),
        primary_metric_name="vocabulary_size",
        primary_metric_value=float(len(vectorizer.vocabulary_)),
        metadata={"ngram_range": "(1,2)", "max_features": 10_000},
    )
    return {"registry": registry_entry, "corpus_size": len(texts)}


def sparse_search(query: str, top_k: int = 20) -> list[dict]:
    """
    Perform sparse TF-IDF keyword search over the scheme corpus.

    Args:
        query: Natural language query string.
        top_k: Number of top results to return.

    Returns:
        list of {"scheme_version_id": str, "sparse_score": float, "rank": int}
        sorted by score descending.
    """
    bundle = load_model(MODEL_TYPE)
    vectorizer: TfidfVectorizer = bundle["vectorizer"]
    tfidf_matrix = bundle["tfidf_matrix"]
    ids: list[str] = bundle["scheme_version_ids"]

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    top_indices = np.argsort(scores)[::-1][:top_k]
    results = [
        {
            "scheme_version_id": ids[i],
            "sparse_score": float(scores[i]),
            "rank": rank + 1,
        }
        for rank, i in enumerate(top_indices)
        if scores[i] > 0
    ]
    return results


def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Merge dense (Qdrant) and sparse (TF-IDF) results using RRF.

    Args:
        dense_results: List of dicts with "scheme_version_id" and "rank".
        sparse_results: List of dicts with "scheme_version_id" and "rank".
        k: RRF constant (default 60 as per the original RRF paper).

    Returns:
        List of {"scheme_version_id": str, "rrf_score": float} sorted by score.
    """
    scores: dict[str, float] = {}

    for result in dense_results:
        sid = result["scheme_version_id"]
        scores[sid] = scores.get(sid, 0.0) + 1.0 / (k + result["rank"])

    for result in sparse_results:
        sid = result["scheme_version_id"]
        scores[sid] = scores.get(sid, 0.0) + 1.0 / (k + result["rank"])

    merged = [
        {"scheme_version_id": sid, "rrf_score": score}
        for sid, score in sorted(scores.items(), key=lambda x: -x[1])
    ]
    return merged
