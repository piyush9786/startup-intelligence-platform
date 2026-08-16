"""Flask REST API for Smart Energy Analytics."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

from src.feature_engineering.features import build_feature_matrix
from src.ml.train import load_model
from src.utils.config_loader import load_config, resolve_path, setup_logging

logger = setup_logging(__name__)
app = Flask(__name__)

_cfg = load_config()
_gold_dir = resolve_path(_cfg["paths"]["gold"])
_model = None
_features = None


def _get_model():
    global _model, _features
    if _model is None:
        _model, _features = load_model()
    return _model, _features


def _read_csv(name: str) -> pd.DataFrame:
    path = _gold_dir / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "smart-energy-analytics"})


@app.route("/api/summary", methods=["GET"])
def summary():
    daily = _read_csv("gold_energy_daily.csv")
    anomalies = _read_csv("gold_energy_anomalies.csv")
    meta_path = resolve_path(_cfg["paths"]["models"]) / "model_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    if daily.empty:
        return jsonify({"error": "Gold data not available. Run pipeline first."}), 503

    return jsonify(
        {
            "total_energy_kwh": float(daily["total_energy_kwh"].sum()),
            "avg_daily_consumption": float(daily.groupby("date")["total_energy_kwh"].sum().mean()),
            "peak_consumption": float(daily["peak_energy_kwh"].max()),
            "meter_count": int(daily["meter_id"].nunique()),
            "anomaly_count": int(anomalies["anomaly_flag"].sum()) if not anomalies.empty else 0,
            "best_model": meta.get("best_model"),
            "model_metrics": meta.get("metrics", {}),
        }
    )


@app.route("/api/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True) or {}
    records = payload.get("records")
    if not records or not isinstance(records, list):
        return jsonify({"error": "Request body must include 'records' list."}), 400

    try:
        df = pd.DataFrame(records)
        required = {"timestamp", "meter_id", "energy_consumption_kwh", "temperature", "humidity", "occupancy"}
        missing = required - set(df.columns)
        if missing:
            return jsonify({"error": f"Missing required fields: {sorted(missing)}"}), 400

        model, feature_cols = _get_model()
        featured, _ = build_feature_matrix(df)
        preds = model.predict(featured[feature_cols])
        return jsonify({"predictions": [float(p) for p in preds]})
    except Exception as exc:
        logger.exception("Prediction failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/predictions", methods=["GET"])
def predictions():
    df = _read_csv("gold_energy_predictions.csv")
    if df.empty:
        return jsonify({"error": "Predictions not available."}), 503
    limit = int(request.args.get("limit", 100))
    return jsonify({"count": len(df), "data": df.head(limit).to_dict(orient="records")})


@app.route("/api/anomalies", methods=["GET"])
def anomalies():
    df = _read_csv("gold_energy_anomalies.csv")
    if df.empty:
        return jsonify({"error": "Anomalies not available."}), 503
    flagged = df[df["anomaly_flag"] == 1] if "anomaly_flag" in df.columns else df
    limit = int(request.args.get("limit", 100))
    return jsonify({"count": len(flagged), "data": flagged.head(limit).to_dict(orient="records")})


@app.route("/api/meters", methods=["GET"])
def meters():
    df = _read_csv("gold_meter_summary.csv")
    if df.empty:
        return jsonify({"error": "Meter summary not available."}), 503
    return jsonify({"count": len(df), "data": df.to_dict(orient="records")})


@app.route("/api/energy/daily", methods=["GET"])
def energy_daily():
    df = _read_csv("gold_energy_daily.csv")
    if df.empty:
        return jsonify({"error": "Daily energy data not available."}), 503

    meter_id = request.args.get("meter_id")
    if meter_id:
        df = df[df["meter_id"] == meter_id]
    limit = int(request.args.get("limit", 500))
    return jsonify({"count": len(df), "data": df.head(limit).to_dict(orient="records")})


def create_app() -> Flask:
    return app


def main() -> None:
    api_cfg = _cfg.get("api", {})
    app.run(host=api_cfg.get("host", "0.0.0.0"), port=api_cfg.get("port", 5000), debug=False)


if __name__ == "__main__":
    main()
