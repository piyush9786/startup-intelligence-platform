"""Machine learning training and prediction pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.feature_engineering.features import build_feature_matrix
from src.utils.config_loader import ensure_dir, load_config, resolve_path, setup_logging

logger = setup_logging(__name__)


def time_series_split(df: pd.DataFrame, test_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("timestamp")
    split_idx = int(len(df) * (1 - test_ratio))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": float(mse),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train_models(config_path: str | None = None) -> dict:
    cfg = load_config(Path(config_path) if config_path else None)
    ml_cfg = cfg["ml"]
    gold_dir = resolve_path(cfg["paths"]["gold"])
    models_dir = ensure_dir(resolve_path(cfg["paths"]["models"]))

    silver_csv = gold_dir / "silver_for_ml.csv"
    if not silver_csv.exists():
        raise FileNotFoundError(f"Missing {silver_csv}. Run spark pipeline first.")

    df = pd.read_csv(silver_csv, parse_dates=["timestamp"])
    featured, feature_cols = build_feature_matrix(df)
    train_df, test_df = time_series_split(featured, ml_cfg["test_size_ratio"])

    X_train = train_df[feature_cols]
    y_train = train_df[ml_cfg["target_column"]]
    X_test = test_df[feature_cols]
    y_test = test_df[ml_cfg["target_column"]]

    candidates = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            random_state=ml_cfg["random_state"],
            n_jobs=-1,
        ),
    }

    results: dict[str, dict] = {}
    best_name = None
    best_rmse = float("inf")
    best_model = None

    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        metrics = evaluate_model(y_test.values, preds)
        results[name] = metrics
        logger.info("Model %s metrics: %s", name, metrics)
        if metrics["rmse"] < best_rmse:
            best_rmse = metrics["rmse"]
            best_name = name
            best_model = model

    assert best_model is not None and best_name is not None
    model_path = models_dir / "best_energy_model.joblib"
    meta_path = models_dir / "model_metadata.json"

    joblib.dump({"model": best_model, "features": feature_cols}, model_path)

    metadata = {
        "best_model": best_name,
        "metrics": results,
        "feature_columns": feature_cols,
        "target_column": ml_cfg["target_column"],
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    test_df = test_df.copy()
    test_df["predicted_energy_kwh"] = best_model.predict(X_test)
    test_df["actual_energy_kwh"] = y_test.values
    test_df["prediction_error"] = test_df["actual_energy_kwh"] - test_df["predicted_energy_kwh"]
    test_df["abs_prediction_error"] = test_df["prediction_error"].abs()

    pred_out = gold_dir / "gold_energy_predictions.csv"
    test_df[
        [
            "timestamp",
            "meter_id",
            "actual_energy_kwh",
            "predicted_energy_kwh",
            "prediction_error",
            "abs_prediction_error",
            "temperature",
            "occupancy",
            "season",
        ]
    ].to_csv(pred_out, index=False)

    logger.info("Saved best model (%s) to %s", best_name, model_path)
    return metadata


def load_model(models_dir: Path | None = None):
    cfg = load_config()
    path = (models_dir or resolve_path(cfg["paths"]["models"])) / "best_energy_model.joblib"
    payload = joblib.load(path)
    return payload["model"], payload["features"]


def predict_from_records(records: list[dict]) -> list[float]:
    model, features = load_model()
    df = pd.DataFrame(records)
    featured, _ = build_feature_matrix(df)
    return model.predict(featured[features]).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train energy consumption models")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    metadata = train_models(config_path=args.config)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
