"""
Model 6 — Isolation Forest: Startup Profile Anomaly Detector

Detects fraudulent, spam, or statistically anomalous startup profiles
at the point of creation or profile update. Anomalous profiles are flagged
in the admin dashboard for manual review before they can receive scheme
recommendations.

Isolation Forest works by randomly partitioning the feature space — anomalies
are isolated quickly (short paths), normal points require many splits.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from apps.ml_engine.services.feature_pipeline import batch_extract_features, extract_features
from apps.ml_engine.services.model_store import load_production_model, save_model

MODEL_TYPE = "isolation_forest"
MODEL_NAME = "isolation_forest_anomaly"
ANOMALY_THRESHOLD = -0.15  # Scores below this are flagged as anomalous


def train_isolation_forest(
    startups_queryset=None,
    *,
    X: np.ndarray | None = None,
    contamination: float = 0.05,
    random_state: int = 42,
    metadata: dict | None = None,
) -> dict:
    """
    Train an Isolation Forest on all known valid startup profiles.

    Args:
        startups_queryset: Queryset of valid StartupProfiles.
        X: Pre-computed feature matrix (used in synthetic training).
        contamination: Expected fraction of outliers in training data.
        random_state: Seed for reproducibility.
        metadata: Optional additional training metadata.

    Returns:
        dict with registry entry.
    """
    if X is None:
        if startups_queryset is None:
            from apps.startups.models import StartupProfile
            startups_queryset = StartupProfile.objects.all()
        X, _ = batch_extract_features(startups_queryset)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X)

    meta = {"contamination": contamination, "random_state": random_state}
    if metadata:
        meta.update(metadata)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=model,
        training_sample_count=len(X),
        primary_metric_name="contamination",
        primary_metric_value=contamination,
        metadata=meta,
    )
    return {"registry": registry_entry}


def score_anomaly(startup) -> tuple[float, bool]:
    """
    Compute the anomaly score for a single StartupProfile.

    Returns:
        (score, is_anomalous): score is a float in roughly (-1, 0.5).
        Negative scores indicate anomalies. is_anomalous is True if
        the score is below ANOMALY_THRESHOLD.
    """
    try:
        model = load_production_model(MODEL_TYPE)
    except FileNotFoundError:
        return 0.0, False  # Fallback if no production model exists

    vec = extract_features(startup).reshape(1, -1)
    score = float(model.decision_function(vec)[0])
    is_anomalous = score < ANOMALY_THRESHOLD

    # Persist result back to the feature store
    from apps.ml_engine.models import MLFeatureStore
    MLFeatureStore.objects.filter(startup_profile=startup).update(
        anomaly_score=score,
        is_anomalous=is_anomalous,
    )
    return score, is_anomalous
