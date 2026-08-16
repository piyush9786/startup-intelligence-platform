# Architecture

## Overview

```
Raw CSV -> Bronze (Parquet) -> Silver (cleaned) -> Gold (analytics CSV)
                                      |
                    +-----------------+------------------+
                    v                 v                  v
              PostgreSQL          ML Training      Anomaly Detection
                    |                 |                  |
                    v                 v                  v
              Warehouse DDL      Flask API         Power BI Gold
```

## Layers

| Layer | Purpose | Format |
|-------|---------|--------|
| Raw | Generated smart-meter readings | CSV |
| Bronze | Ingested data with lineage | Parquet |
| Silver | Cleaned, validated, time dimensions | Parquet |
| Gold | Aggregated analytics datasets | CSV + Parquet |

## Components

- **PySpark**: Scalable local processing with medallion architecture
- **Hive DDL**: External table definitions for Hadoop/Hive environments
- **PostgreSQL**: Analytical warehouse (`fact_*`, `dim_*` tables)
- **Scikit-learn**: Linear Regression + Random Forest; Isolation Forest for anomalies
- **Flask**: REST API serving predictions and Gold data
- **Power BI**: Consumes Gold CSV files directly

## Data Flow

1. Configurable generator creates 15-minute interval meter readings
2. PySpark enforces schema, deduplicates, validates ranges
3. Gold aggregations: daily, hourly, meter summary, weather analysis
4. ML pipeline uses time-aware split (no shuffle leakage)
5. Anomalies exported to `gold_energy_anomalies.csv`
6. Flask reads Gold datasets and trained model
