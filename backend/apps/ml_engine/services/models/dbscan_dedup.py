"""
Model 9 — DBSCAN Clustering: Scheme Deduplication

Uses DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
on scheme embedding vectors from Qdrant to identify clusters of near-duplicate
scheme versions. Near-duplicates are flagged for admin review so that
redundant entries don't inflate recommendation counts.

Unlike K-Means, DBSCAN doesn't require specifying the number of clusters
and naturally handles outliers (unique schemes) by labelling them as noise (-1).
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN

from apps.ml_engine.services.model_store import save_model

MODEL_TYPE = "dbscan"
MODEL_NAME = "dbscan_scheme_dedup"


def find_duplicate_schemes(
    scheme_embeddings: list[dict],
    *,
    eps: float = 0.08,
    min_samples: int = 2,
) -> dict:
    """
    Detect near-duplicate scheme versions using DBSCAN on embedding vectors.

    Args:
        scheme_embeddings: List of dicts with:
            - "scheme_version_id": str
            - "vector": list[float] — embedding from Qdrant
        eps: Maximum cosine distance between two points to be considered neighbours.
        min_samples: Minimum cluster size to form a core point.

    Returns:
        dict with:
            - "duplicate_groups": list of lists of scheme_version_ids
            - "unique_count": number of unique schemes (noise = -1 label)
            - "registry": MLModelRegistry entry
    """
    if not scheme_embeddings:
        return {"duplicate_groups": [], "unique_count": 0, "registry": None}

    ids = [item["scheme_version_id"] for item in scheme_embeddings]
    vectors = np.array([item["vector"] for item in scheme_embeddings], dtype=np.float32)

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors_norm = vectors / norms

    model = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=-1)
    labels = model.fit_predict(vectors_norm)

    # Group scheme_version_ids by cluster label (excluding noise = -1)
    clusters: dict[int, list[str]] = {}
    for sid, label in zip(ids, labels, strict=False):
        if label == -1:
            continue
        clusters.setdefault(label, []).append(sid)

    duplicate_groups = [group for group in clusters.values() if len(group) >= 2]
    unique_count = int(np.sum(labels == -1))

    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=model,
        training_sample_count=len(ids),
        primary_metric_name="duplicate_group_count",
        primary_metric_value=float(len(duplicate_groups)),
        metadata={"eps": eps, "min_samples": min_samples},
    )

    return {
        "duplicate_groups": duplicate_groups,
        "unique_count": unique_count,
        "registry": registry_entry,
    }
