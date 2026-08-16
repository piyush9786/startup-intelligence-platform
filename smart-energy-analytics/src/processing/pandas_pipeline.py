"""Pandas medallion pipeline fallback when PySpark is unavailable."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config_loader import ensure_dir, load_config, resolve_path, setup_logging

logger = setup_logging(__name__)


def _find_input_csv(raw_dir: Path, sample_dir: Path) -> Path:
    for directory in (raw_dir, sample_dir):
        candidate = directory / "smart_meter_readings.csv"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No smart_meter_readings.csv found in data/raw or data/sample")


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def run_pipeline_pandas(config_path: str | None = None) -> dict[str, Path]:
    cfg = load_config(Path(config_path) if config_path else None)
    paths = cfg["paths"]

    raw_dir = ensure_dir(resolve_path(paths["raw"]))
    sample_dir = ensure_dir(resolve_path("data/sample"))
    bronze_dir = ensure_dir(resolve_path(paths["bronze"]))
    silver_dir = ensure_dir(resolve_path(paths["silver"]))
    gold_dir = ensure_dir(resolve_path(paths["gold"]))

    input_csv = _find_input_csv(raw_dir, sample_dir)
    logger.info("Running pandas BRONZE/SILVER/GOLD from %s", input_csv)

    df = pd.read_csv(input_csv)
    df["ingestion_ts"] = pd.Timestamp.utcnow()
    df["source_file"] = input_csv.name
    bronze_path = bronze_dir / "bronze_energy_readings.parquet"
    df.to_parquet(bronze_path, index=False)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["meter_id", "timestamp"])
    df = df[df["timestamp"].notna()]
    df = df[
        (df["energy_consumption_kwh"] >= 0)
        & (df["energy_consumption_kwh"] <= 50)
        & (df["voltage"].between(180, 260))
        & (df["power_factor"].between(0.5, 1.0))
    ]

    numeric_cols = [
        "voltage", "current", "power_factor", "active_power_kw",
        "reactive_power_kvar", "energy_consumption_kwh", "temperature",
        "humidity", "occupancy", "appliance_load", "hvac_load", "lighting_load",
    ]
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())

    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute
    df["day_of_week"] = df["timestamp"].dt.dayofweek + 1
    df["day_name"] = df["timestamp"].dt.day_name()
    df["week"] = df["timestamp"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["timestamp"].dt.quarter
    df["is_weekend"] = df["day_of_week"].isin([6, 7])
    df["season"] = np.select(
        [
            df["month"].isin([12, 1, 2]),
            df["month"].isin([3, 4, 5]),
            df["month"].isin([6, 7, 8]),
        ],
        ["winter", "spring", "summer"],
        default="autumn",
    )

    silver_path = silver_dir / "silver_energy_readings.parquet"
    df.to_parquet(silver_path, index=False)

    daily = (
        df.groupby(
            ["date", "meter_id", "year", "month", "day", "day_name", "day_of_week", "is_weekend", "season"],
            as_index=False,
        )
        .agg(
            total_energy_kwh=("energy_consumption_kwh", "sum"),
            avg_energy_kwh=("energy_consumption_kwh", "mean"),
            peak_energy_kwh=("energy_consumption_kwh", "max"),
            avg_temperature=("temperature", "mean"),
            avg_humidity=("humidity", "mean"),
            avg_occupancy=("occupancy", "mean"),
            reading_count=("energy_consumption_kwh", "count"),
        )
        .sort_values(["date", "meter_id"])
    )

    hourly = (
        df.groupby(
            ["date", "hour", "meter_id", "year", "month", "day_name", "is_weekend", "season"],
            as_index=False,
        )
        .agg(
            total_energy_kwh=("energy_consumption_kwh", "sum"),
            avg_energy_kwh=("energy_consumption_kwh", "mean"),
            peak_power_kw=("active_power_kw", "max"),
            avg_temperature=("temperature", "mean"),
            avg_occupancy=("occupancy", "mean"),
        )
        .sort_values(["date", "hour", "meter_id"])
    )

    meter_summary = (
        df.groupby("meter_id", as_index=False)
        .agg(
            total_energy_kwh=("energy_consumption_kwh", "sum"),
            avg_energy_kwh=("energy_consumption_kwh", "mean"),
            peak_energy_kwh=("energy_consumption_kwh", "max"),
            std_energy_kwh=("energy_consumption_kwh", "std"),
            avg_temperature=("temperature", "mean"),
            total_readings=("energy_consumption_kwh", "count"),
            first_reading_date=("date", "min"),
            last_reading_date=("date", "max"),
        )
        .sort_values("meter_id")
    )

    weather_analysis = (
        df.groupby(["weather_condition", "season", "is_weekend"], as_index=False)
        .agg(
            total_energy_kwh=("energy_consumption_kwh", "sum"),
            avg_energy_kwh=("energy_consumption_kwh", "mean"),
            avg_temperature=("temperature", "mean"),
            reading_count=("energy_consumption_kwh", "count"),
        )
        .sort_values(["weather_condition", "season"])
    )

    outputs: dict[str, Path] = {}
    gold_map = {
        "gold_energy_daily": daily,
        "gold_energy_hourly": hourly,
        "gold_meter_summary": meter_summary,
        "gold_weather_energy_analysis": weather_analysis,
    }
    for name, frame in gold_map.items():
        csv_path = gold_dir / f"{name}.csv"
        parquet_path = gold_dir / f"{name}.parquet"
        _write_csv(frame, csv_path)
        frame.to_parquet(parquet_path, index=False)
        outputs[name] = csv_path

    silver_csv = gold_dir / "silver_for_ml.csv"
    ml_cols = [
        "timestamp", "meter_id", "energy_consumption_kwh", "temperature", "humidity",
        "occupancy", "hour", "day_of_week", "month", "is_weekend", "season",
        "weather_condition", "active_power_kw", "hvac_load", "lighting_load",
        "appliance_load", "is_anomaly_source", "anomaly_type_source",
    ]
    _write_csv(df[ml_cols], silver_csv)
    outputs["silver_for_ml"] = silver_csv

    logger.info("Pandas pipeline complete.")
    return outputs
