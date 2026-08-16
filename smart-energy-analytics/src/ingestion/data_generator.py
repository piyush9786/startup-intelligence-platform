"""Smart meter energy consumption data generator."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config_loader import ensure_dir, load_config, resolve_path, setup_logging

logger = setup_logging(__name__)

WEATHER_CONDITIONS = ["clear", "cloudy", "rain", "storm", "fog"]


def _season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _base_temperature(ts: pd.Timestamp, rng: np.random.Generator) -> float:
    day_of_year = ts.dayofyear
    seasonal = 18 + 12 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    daily = 4 * np.sin(2 * np.pi * (ts.hour + ts.minute / 60 - 14) / 24)
    return float(seasonal + daily + rng.normal(0, 1.5))


def generate_meter_data(
    meter_id: str,
    start: datetime,
    end: datetime,
    interval_minutes: int,
    anomaly_rate: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    rows: list[dict] = []
    ts = start
    meter_factor = rng.uniform(0.85, 1.25)

    while ts <= end:
        hour = ts.hour + ts.minute / 60
        is_weekend = ts.weekday() >= 5
        season = _season(ts.month)

        temperature = _base_temperature(pd.Timestamp(ts), rng)
        humidity = float(np.clip(55 + (25 - temperature) * 0.8 + rng.normal(0, 8), 15, 98))
        weather = rng.choice(
            WEATHER_CONDITIONS,
            p=[0.45, 0.25, 0.15, 0.05, 0.10],
        )

        occupancy = float(
            np.clip(
                (0.35 if is_weekend else 0.55)
                + 0.35 * np.sin(2 * np.pi * (hour - 7) / 24)
                + rng.normal(0, 0.08),
                0.05,
                1.0,
            )
        )

        hvac_load = float(
            meter_factor
            * (
                0.8
                + max(0, (22 - temperature) * 0.12)
                + max(0, (temperature - 26) * 0.15)
            )
            * (1.2 if season in ("summer", "winter") else 0.9)
        )
        lighting_load = float(meter_factor * (0.15 + (0.45 if hour < 7 or hour > 18 else 0.05)))
        appliance_load = float(meter_factor * occupancy * (0.4 + rng.uniform(0, 0.3)))

        active_power_kw = float(
            hvac_load + lighting_load + appliance_load + rng.normal(0, 0.05)
        )
        active_power_kw = max(active_power_kw, 0.05)

        is_anomaly = rng.random() < anomaly_rate
        if is_anomaly:
            active_power_kw *= rng.choice([2.5, 3.0, 0.1, 0.05])
            anomaly_type = rng.choice(["spike", "drop", "sensor_fault"])
        else:
            anomaly_type = None

        energy_consumption_kwh = active_power_kw * (interval_minutes / 60)
        voltage = float(rng.normal(230, 3))
        current = float((active_power_kw * 1000) / max(voltage, 1))
        power_factor = float(np.clip(rng.normal(0.92, 0.04), 0.75, 1.0))
        reactive_power_kvar = float(active_power_kw * np.tan(np.arccos(power_factor)))

        rows.append(
            {
                "timestamp": ts.isoformat(),
                "meter_id": meter_id,
                "voltage": round(voltage, 2),
                "current": round(current, 3),
                "power_factor": round(power_factor, 3),
                "active_power_kw": round(active_power_kw, 4),
                "reactive_power_kvar": round(reactive_power_kvar, 4),
                "energy_consumption_kwh": round(energy_consumption_kwh, 6),
                "temperature": round(temperature, 2),
                "humidity": round(humidity, 2),
                "weather_condition": weather,
                "occupancy": round(occupancy, 3),
                "appliance_load": round(appliance_load, 4),
                "hvac_load": round(hvac_load, 4),
                "lighting_load": round(lighting_load, 4),
                "is_anomaly_source": bool(is_anomaly),
                "anomaly_type_source": anomaly_type,
            }
        )
        ts += timedelta(minutes=interval_minutes)

    return pd.DataFrame(rows)


def generate_dataset(config_path: str | None = None, sample: bool = False) -> Path:
    cfg = load_config(Path(config_path) if config_path else None)
    gen_cfg = cfg["data_generation"]

    if sample:
        gen_cfg = {
            **gen_cfg,
            "num_meters": 3,
            "start_date": "2024-01-01",
            "end_date": "2024-01-14",
            "output_dir": gen_cfg.get("sample_output_dir", "data/sample"),
        }

    rng = np.random.default_rng(gen_cfg["seed"])
    start = datetime.fromisoformat(gen_cfg["start_date"])
    end = datetime.fromisoformat(gen_cfg["end_date"] + " 23:45:00")

    output_dir = ensure_dir(resolve_path(gen_cfg["output_dir"]))
    frames: list[pd.DataFrame] = []

    for i in range(1, gen_cfg["num_meters"] + 1):
        meter_id = f"MTR{i:03d}"
        logger.info("Generating data for %s", meter_id)
        df = generate_meter_data(
            meter_id=meter_id,
            start=start,
            end=end,
            interval_minutes=gen_cfg["interval_minutes"],
            anomaly_rate=gen_cfg["anomaly_rate"],
            rng=rng,
        )
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    output_file = output_dir / "smart_meter_readings.csv"
    combined.to_csv(output_file, index=False)
    logger.info("Saved %s rows to %s", len(combined), output_file)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate smart meter energy data")
    parser.add_argument("--sample", action="store_true", help="Generate smaller sample dataset")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    args = parser.parse_args()
    generate_dataset(config_path=args.config, sample=args.sample)


if __name__ == "__main__":
    main()
