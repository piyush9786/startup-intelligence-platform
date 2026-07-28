"""
Model 5 — AdaBoost Classifier: Readiness Improvement Predictor

Predicts the probability that a startup will transition from its current
"blocked" or "ready_with_recommendations" readiness status to "READY"
within the next 30 days, given its current profile completeness gaps.

This is shown in the UI as an "AI Readiness Boost Probability" indicator.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier

from apps.ml_engine.services.feature_pipeline import extract_features
from apps.ml_engine.services.model_store import save_model

MODEL_TYPE = "adaboost"
MODEL_NAME = "adaboost_readiness_predictor"


def train_adaboost(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_estimators: int = 50,
    random_state: int = 42,
    metadata: dict | None = None,
) -> dict:
    """
    Train an AdaBoost classifier on startup readiness transition labels.

    Args:
        X: Feature matrix of shape (n_samples, n_features).
        y: Binary labels (1 = became READY within 30 days, 0 = did not).
        n_estimators: Number of weak learners in the ensemble.
        random_state: Seed for reproducibility.
        metadata: Optional additional training metadata.

    Returns:
        dict with registry entry and accuracy metrics.
    """
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    base_estimator = DecisionTreeClassifier(max_depth=2, random_state=random_state)
    model = AdaBoostClassifier(
        estimator=base_estimator,
        n_estimators=n_estimators,
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    accuracy = float(accuracy_score(y_test, model.predict(X_test)))
    try:
        roc_auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    except Exception:
        roc_auc = None

    meta = {
        "learning_rate": 1.0,
        "n_estimators": n_estimators,
        "accuracy": accuracy,
        "random_state": random_state,
    }
    if metadata:
        meta.update(metadata)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=model,
        training_sample_count=len(X_train),
        primary_metric_name="roc_auc",
        primary_metric_value=roc_auc,
        metadata=meta,
    )
    return {"registry": registry_entry, "accuracy": accuracy, "roc_auc": roc_auc}


def predict_readiness_improvement(startup) -> float:
    """
    Predict the probability that the startup will become READY in 30 days.

    Returns:
        float: Probability [0.0, 1.0].
    """
    try:
        from apps.ml_engine.services.model_store import load_production_model
        model = load_production_model(MODEL_TYPE)
    except FileNotFoundError:
        return 0.0

    vec = extract_features(startup).reshape(1, -1)
    prob = float(model.predict_proba(vec)[0][1])
    return round(prob, 4)
