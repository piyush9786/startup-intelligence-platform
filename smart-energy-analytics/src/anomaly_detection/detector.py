"""Anomaly detection for smart meter energy consumption."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from src.utils.config_loader import load_config, resolve_path, setup_logging

logger = setup_logging(__name__)


def detect_anomalies(config_path: str | None = None) -> Path:
    cfg = load_config(Path(config_path) if config_path else None)
    gold_dir = resolve_path(cfg["paths"]["gold"])
    silver_csv = gold_dir / "silver_for_ml.csv"
    if not silver_csv.exists():
        raise FileNotFoundError(f"Missing {silver_csv}")

    df = pd.read_csv(silver_csv, parse_dates=["timestamp"])
    feature_cols = [
        "energy_consumption_kwh",
        "active_power_kw",
        "temperature",
        "humidity",
        "occupancy",
        "hvac_load",
    ]

    model = IsolationForest(contamination=0.02, random_state=42, n_jobs=-1)
    scores = model.fit_predict(df[feature_cols])
    anomaly_scores = model.decision_function(df[feature_cols])

    df["anomaly_flag"] = (scores == -1).astype(int)
    df["anomaly_score"] = anomaly_scores
    df["anomaly_reason"] = "normal"
    df.loc[df["anomaly_flag"] == 1, "anomaly_reason"] = df.loc[
        df["anomaly_flag"] == 1, "anomaly_type_source"
    ].fillna("statistical_outlier")

    out = gold_dir / "gold_energy_anomalies.csv"
    df[
        [
            "timestamp",
            "meter_id",
            "energy_consumption_kwh",
            "active_power_kw",
            "temperature",
            "anomaly_flag",
            "anomaly_score",
            "anomaly_reason",
            "season",
            "weather_condition",
        ]
    ].to_csv(out, index=False)

    logger.info("Saved anomalies to %s (%s anomalies)", out, df["anomaly_flag"].sum())
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect energy consumption anomalies")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    detect_anomalies(config_path=args.config)


if __name__ == "__main__":
    main()
