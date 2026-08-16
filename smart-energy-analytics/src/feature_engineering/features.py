"""Feature engineering for energy consumption prediction."""

from __future__ import annotations

import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"])
        out["hour"] = out["timestamp"].dt.hour
        out["day_of_week"] = out["timestamp"].dt.dayofweek + 1
        out["month"] = out["timestamp"].dt.month
        out["is_weekend"] = (out["day_of_week"].isin([6, 7])).astype(int)
        out["season"] = out.get("season", pd.Series(["unknown"] * len(out)))

    season_map = {"winter": 0, "spring": 1, "summer": 2, "autumn": 3}
    if "season" in out.columns and out["season"].dtype == object:
        out["season_code"] = out["season"].map(season_map).fillna(0).astype(int)
    return out


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["meter_id", "timestamp"]).copy()
    out["prev_consumption"] = out.groupby("meter_id")["energy_consumption_kwh"].shift(1)
    out["rolling_consumption_4"] = (
        out.groupby("meter_id")["energy_consumption_kwh"]
        .transform(lambda s: s.rolling(window=4, min_periods=1).mean())
    )
    out["lag_consumption_1"] = out.groupby("meter_id")["energy_consumption_kwh"].shift(1)
    out["prev_consumption"] = out["prev_consumption"].fillna(out["energy_consumption_kwh"])
    out["rolling_consumption_4"] = out["rolling_consumption_4"].fillna(out["energy_consumption_kwh"])
    out["lag_consumption_1"] = out["lag_consumption_1"].fillna(out["energy_consumption_kwh"])
    return out


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    featured = add_time_features(df)
    featured = add_lag_features(featured)
    feature_cols = [
        "hour",
        "day_of_week",
        "month",
        "temperature",
        "humidity",
        "occupancy",
        "prev_consumption",
        "rolling_consumption_4",
        "lag_consumption_1",
        "is_weekend",
        "season_code",
    ]
    return featured, feature_cols
