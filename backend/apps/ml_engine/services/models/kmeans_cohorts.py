"""
Model 3 — K-Means Clustering: Startup Cohort Segmentation

Groups startups into N cohorts based on their 28-dimensional feature vectors.
Cohorts allow the recommendation engine to target scheme suggestions specifically
to similar startup profiles (e.g., early-stage fintech vs. growth-stage agritech).
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from apps.ml_engine.services.feature_pipeline import batch_extract_features, extract_features
from apps.ml_engine.services.model_store import load_production_model, save_model

MODEL_TYPE = "kmeans"
MODEL_NAME = "kmeans_startup_cohorts"
DEFAULT_N_CLUSTERS = 8


def train_kmeans(
    startups_queryset=None,
    *,
    n_clusters: int = DEFAULT_N_CLUSTERS,
    X: np.ndarray | None = None,
    ids: list[int] | None = None,
    random_state: int = 42,
    metadata: dict | None = None,
) -> dict:
    """
    Train a K-Means model on startup feature vectors.

    Args:
        startups_queryset: Django queryset of StartupProfile objects.
        n_clusters: Number of cohorts to create.
        X: Pre-computed feature matrix (used in synthetic training).
        ids: Aligned list of startup PKs for X.
        random_state: Seed for reproducibility.
        metadata: Optional additional training metadata.

    Returns:
        dict with model registry entry and silhouette score.
    """
    if X is None:
        if startups_queryset is None:
            from apps.startups.models import StartupProfile
            startups_queryset = StartupProfile.objects.all()
        X, ids = batch_extract_features(startups_queryset)

    if len(X) < n_clusters:
        n_clusters = max(2, len(X) // 2)

    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    model.fit(X)

    silhouette = float(silhouette_score(X, model.labels_)) if len(X) > n_clusters else 0.0

    meta = {"n_clusters": n_clusters, "random_state": random_state}
    if metadata:
        meta.update(metadata)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=model,
        training_sample_count=len(X),
        primary_metric_name="silhouette_score",
        primary_metric_value=silhouette,
        metadata=meta,
    )

    # Persist cohort IDs back to feature store only if training on real DB ids
    is_synthetic = meta.get("training_data_source") == "synthetic"
    if ids and not is_synthetic:
        _persist_cohort_assignments(model, X, ids)

    return {"registry": registry_entry, "silhouette_score": silhouette, "n_clusters": n_clusters}


def _persist_cohort_assignments(model: KMeans, X: np.ndarray, ids: list[int]) -> None:
    """Write cluster labels back to MLFeatureStore and StartupProfile."""
    from apps.ml_engine.models import MLFeatureStore
    from apps.startups.models import StartupProfile

    labels = model.predict(X)
    for pk, label in zip(ids, labels, strict=False):
        MLFeatureStore.objects.filter(startup_profile_id=pk).update(cohort_id=int(label))
        StartupProfile.objects.filter(pk=pk).update(ml_cohort_id=int(label))


def assign_cohort(startup) -> int:
    """
    Predict the cohort for a single StartupProfile using the active K-Means model.

    Returns:
        int: Cohort / cluster ID (0 to N_CLUSTERS-1).
    """
    try:
        model = load_production_model(MODEL_TYPE)
    except FileNotFoundError:
        return 0  # Fallback cohort if no production model exists

    vec = extract_features(startup).reshape(1, -1)
    cohort = int(model.predict(vec)[0])
    return cohort
