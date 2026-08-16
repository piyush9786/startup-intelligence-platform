# ML Guide

## Models

- **Linear Regression** — baseline interpretable model
- **Random Forest Regressor** — captures non-linear HVAC/occupancy patterns

## Features

hour, day_of_week, month, temperature, humidity, occupancy, prev_consumption, rolling_consumption_4, lag_consumption_1, is_weekend, season_code

## Validation

Time-aware train/test split (last 20% chronologically). No random shuffle to prevent leakage.

## Metrics

MAE, MSE, RMSE, R² computed on hold-out test set. Best model selected by lowest RMSE.

## Artifacts

- `models/best_energy_model.joblib` — serialized model + feature list
- `models/model_metadata.json` — metrics for both models
- `data/gold/gold_energy_predictions.csv` — actual vs predicted on test set

## Anomaly Detection

Isolation Forest on consumption, power, temperature, humidity, occupancy, HVAC load.
Outputs: anomaly_flag, anomaly_score, anomaly_reason.

## Retrain

```bash
py scripts/run_pipeline.py --sample
```
