"""
Model 4 — SVM Classifier: Scheme Success Probability Ranker

Predicts the probability that a startup will successfully acquire a given
government scheme based on the startup's feature profile and the scheme's
category/stage/amount parameters.

Output is a float [0.0, 1.0] — the higher the score, the more likely the
startup is to succeed if it applies to that scheme.
"""
from __future__ import annotations

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from apps.ml_engine.services.feature_pipeline import extract_features
from apps.ml_engine.services.model_store import load_model, next_version, save_model

MODEL_TYPE = "svm"
MODEL_NAME = "svm_scheme_ranker"


def _scheme_features(scheme_version) -> np.ndarray:
    """Extract 4 numeric features from a SchemeVersion."""
    min_amt = float(scheme_version.minimum_amount or 0)
    max_amt = float(scheme_version.maximum_amount or 0)
    has_equity = 1.0 if scheme_version.equity_required else 0.0
    is_open = 1.0 if scheme_version.application_status == "open" else 0.0
    return np.array([min_amt / 1e7, max_amt / 1e7, has_equity, is_open], dtype=np.float64)


def train_svm(
    X: np.ndarray,
    y: np.ndarray,
    *,
    random_state: int = 42,
) -> dict:
    """
    Train an SVM classifier with probability output.

    Args:
        X: Feature matrix of shape (n_samples, n_features).
        y: Binary labels (1 = scheme acquired, 0 = not acquired).
        random_state: Seed for reproducibility.

    Returns:
        dict with registry entry and accuracy metrics.
    """
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = CalibratedClassifierCV(
        SVC(kernel="rbf", class_weight="balanced", random_state=random_state),
        ensemble=False,
    )
    model.fit(X_train_scaled, y_train)

    accuracy = float(accuracy_score(y_test, model.predict(X_test_scaled)))

    # Package scaler + model together so we don't need separate storage
    bundle = {"scaler": scaler, "model": model}
    version = next_version(MODEL_TYPE)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=bundle,
        version=version,
        training_sample_count=len(X_train),
        primary_metric_name="accuracy",
        primary_metric_value=accuracy,
        metadata={"kernel": "rbf", "random_state": random_state},
    )
    return {"registry": registry_entry, "accuracy": accuracy}


def predict_scheme_probability(startup, scheme_version) -> float:
    """
    Predict the probability of success for a startup-scheme pair.

    Args:
        startup: StartupProfile instance.
        scheme_version: SchemeVersion instance.

    Returns:
        float: Probability [0.0, 1.0] of successful application.
    """
    bundle = load_model(MODEL_TYPE)
    scaler = bundle["scaler"]
    model = bundle["model"]

    startup_vec = extract_features(startup)
    scheme_vec = _scheme_features(scheme_version)
    combined = np.concatenate([startup_vec, scheme_vec]).reshape(1, -1)
    combined_scaled = scaler.transform(combined)

    prob = float(model.predict_proba(combined_scaled)[0][1])
    return round(prob, 6)
