"""Automated tests for Smart Energy Analytics platform."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.anomaly_detection.detector import detect_anomalies
from src.feature_engineering.features import build_feature_matrix
from src.ingestion.data_generator import generate_dataset
from src.ml.train import train_models
from src.processing.spark_pipeline import run_pipeline


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


def test_data_generation(project_root: Path):
    output = generate_dataset(sample=True)
    assert output.exists()
    df = pd.read_csv(output)
    assert len(df) > 0
    required = {
        "timestamp",
        "meter_id",
        "energy_consumption_kwh",
        "temperature",
        "humidity",
        "occupancy",
    }
    assert required.issubset(df.columns)
    assert df["timestamp"].isna().sum() == 0


def test_spark_pipeline(project_root: Path):
    run_pipeline()
    gold_dir = project_root / "data" / "gold"
    for name in [
        "gold_energy_daily.csv",
        "gold_energy_hourly.csv",
        "gold_meter_summary.csv",
        "gold_weather_energy_analysis.csv",
    ]:
        path = gold_dir / name
        assert path.exists(), f"Missing {path}"
        df = pd.read_csv(path)
        assert len(df) > 0


def test_feature_engineering(project_root: Path):
    silver = project_root / "data" / "gold" / "silver_for_ml.csv"
    df = pd.read_csv(silver, parse_dates=["timestamp"])
    featured, cols = build_feature_matrix(df)
    for col in cols:
        assert col in featured.columns
    assert featured["prev_consumption"].notna().all()


def test_ml_training(project_root: Path):
    metadata = train_models()
    assert "best_model" in metadata
    assert "metrics" in metadata
    model_path = project_root / "models" / "best_energy_model.joblib"
    assert model_path.exists()
    pred_path = project_root / "data" / "gold" / "gold_energy_predictions.csv"
    assert pred_path.exists()


def test_anomaly_detection(project_root: Path):
    out = detect_anomalies()
    assert out.exists()
    df = pd.read_csv(out)
    assert "anomaly_flag" in df.columns
    assert "anomaly_score" in df.columns


def test_api_health_and_predict(project_root: Path):
    from src.api.app import create_app

    app = create_app()
    client = app.test_client()

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "healthy"

    silver = pd.read_csv(project_root / "data" / "gold" / "silver_for_ml.csv")
    record = silver.iloc[0].to_dict()
    resp = client.post("/api/predict", json={"records": [record]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "predictions" in body
    assert len(body["predictions"]) == 1


def test_model_metadata(project_root: Path):
    meta_path = project_root / "models" / "model_metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for model_name, metrics in meta["metrics"].items():
        for key in ("mae", "mse", "rmse", "r2"):
            assert key in metrics, f"{model_name} missing {key}"
