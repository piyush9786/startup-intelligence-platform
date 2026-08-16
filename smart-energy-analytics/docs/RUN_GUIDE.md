# Run Guide

## Prerequisites

- Python 3.11+ (tested with 3.13/3.14)
- Java 8+ (required for PySpark)

## Local Execution

```bash
cd smart-energy-analytics
py -m pip install -r requirements.txt
py scripts/run_pipeline.py --sample
py -m pytest tests/ -v
py -m src.api.app
```

Full dataset (edit `config/data_config.yaml` date range):

```bash
py scripts/run_pipeline.py
```

Skip regeneration:

```bash
py scripts/run_pipeline.py --sample --skip-generate
```

## Docker Execution

```bash
docker-compose up --build
```

- API: http://localhost:5000
- PostgreSQL: localhost:5432 (smart_energy / energy_user / energy_pass)

## PostgreSQL Setup (optional local)

```bash
psql -U postgres -f sql/warehouse/create_tables.sql
```

## Individual Steps

```bash
py -m src.ingestion.data_generator --sample
py -m src.processing.spark_pipeline
py -m src.ml.train
py -m src.anomaly_detection.detector
```
