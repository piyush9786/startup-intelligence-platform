"""
Model 8 — Random Forest Regressor: Capital Runway Forecaster

Upgrades the deterministic `capital_planner_engine.py` with a learned model
that considers a startup's sector, stage, team size, and historical funding
patterns to output a more realistic capital runway prediction.

The deterministic engine is still used for exact scenario math; this model
provides a "ML-adjusted" runway that accounts for sector-specific burn patterns.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from apps.ml_engine.services.feature_pipeline import extract_features
from apps.ml_engine.services.model_store import load_model, next_version, save_model

MODEL_TYPE = "random_forest"
MODEL_NAME = "rf_capital_forecaster"


def train_random_forest(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_estimators: int = 100,
    random_state: int = 42,
    metadata: dict | None = None,
) -> dict:
    """
    Train a Random Forest Regressor to predict runway months.

    Args:
        X: Feature matrix of shape (n_samples, n_features + 4 capital features).
            Capital features: [available_capital, monthly_revenue, fixed_costs, variable_costs]
            appended to the standard 28-dim startup feature vector.
        y: Target values — actual runway months (float).
        n_estimators: Number of trees.
        random_state: Seed for reproducibility.
        metadata: Optional additional training metadata.

    Returns:
        dict with registry entry and MAE metric.
    """
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=12,
        min_samples_leaf=3,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    mae = float(mean_absolute_error(y_test, model.predict(X_test)))

    version = next_version(MODEL_TYPE)
    meta = {"n_estimators": n_estimators, "max_depth": 12, "random_state": random_state}
    if metadata:
        meta.update(metadata)
    registry_entry = save_model(
        model_type=MODEL_TYPE,
        model_name=MODEL_NAME,
        model_obj=model,
        version=version,
        training_sample_count=len(X_train),
        primary_metric_name="mae_months",
        primary_metric_value=mae,
        metadata=meta,
    )
    return {"registry": registry_entry, "mae_months": mae}


def predict_ml_runway(
    startup,
    *,
    available_capital: float,
    monthly_revenue: float,
    fixed_costs: float,
    variable_costs: float,
) -> float:
    """
    Predict the ML-adjusted capital runway for a startup.

    Args:
        startup: StartupProfile instance.
        available_capital, monthly_revenue, fixed_costs, variable_costs: capital inputs.

    Returns:
        float: Predicted runway in months (capped at 99.0).
    """
    model = load_model(MODEL_TYPE)
    startup_vec = extract_features(startup)
    capital_vec = np.array(
        [
            available_capital / 1e7,
            monthly_revenue / 1e7,
            fixed_costs / 1e7,
            variable_costs / 1e7,
        ],
        dtype=np.float64,
    )
    combined = np.concatenate([startup_vec, capital_vec]).reshape(1, -1)
    prediction = float(model.predict(combined)[0])
    return round(min(99.0, max(0.0, prediction)), 1)
