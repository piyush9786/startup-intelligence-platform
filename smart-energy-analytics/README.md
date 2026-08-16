# Smart Energy Analytics and Consumption Prediction Platform

End-to-end smart-meter analytics: data generation, PySpark medallion pipeline, PostgreSQL warehouse DDL, ML prediction, anomaly detection, Flask API, and Power BI-ready Gold datasets.

## Quick Start (Local)

```bash
cd smart-energy-analytics
py -m pip install -r requirements.txt
py scripts/run_pipeline.py --sample
py -m src.api.app
```

API: http://localhost:5000/health

## Project Structure

- `src/ingestion` — smart meter data generator
- `src/processing` — PySpark Bronze/Silver/Gold pipeline
- `src/ml` — regression training and prediction
- `src/anomaly_detection` — Isolation Forest anomalies
- `src/api` — Flask REST API
- `data/gold/` — Power BI-ready CSV datasets
- `sql/` — Hive DDL and PostgreSQL warehouse scripts
- `docs/` — architecture, API, ML, Power BI, run guides

## Docker

```bash
docker-compose up --build
```

## Tests

```bash
py -m pytest tests/ -v
```

## Gold Datasets (Power BI)

Import from `data/gold/`:

- `gold_energy_daily.csv`
- `gold_energy_hourly.csv`
- `gold_meter_summary.csv`
- `gold_energy_predictions.csv`
- `gold_energy_anomalies.csv`
- `gold_weather_energy_analysis.csv`

See `docs/POWER_BI_GUIDE.md` for dashboard setup.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/summary` | Platform KPI summary |
| POST | `/api/predict` | Predict consumption |
| GET | `/api/predictions` | Stored predictions |
| GET | `/api/anomalies` | Detected anomalies |
| GET | `/api/meters` | Meter summaries |
| GET | `/api/energy/daily` | Daily consumption |

See `docs/API_GUIDE.md` for request/response examples.
