# CDAC Interview Guide

## Why PySpark?

Handles large smart-meter volumes with distributed processing. Local mode runs on a laptop; same code scales to cluster.

## Why Bronze/Silver/Gold?

Medallion architecture separates raw ingestion, cleaned conforming data, and business-ready analytics. Enables auditability and incremental processing.

## Why PostgreSQL?

Relational warehouse for dimensional modeling (fact/dim tables), indexing, and SQL analytics alongside batch pipeline.

## Hive Role

Hive DDL defines external Parquet tables over HDFS paths — standard in Hadoop ecosystems for SQL-on-big-data without moving raw files.

## Feature Engineering

Lag and rolling consumption capture temporal patterns. Season/weekend/temperature/occupancy reflect real consumption drivers.

## Time-Aware Split

Chronological split prevents future data leaking into training — critical for time-series forecasting validity.

## Model Selection

Random Forest typically wins on non-linear HVAC/occupancy interactions; Linear Regression serves as baseline. RMSE selects best model.

## Anomaly Detection

Isolation Forest isolates unusual multivariate patterns (spikes, drops, sensor faults) without labeled anomaly data.

## Flask API

Serves real-time predictions and Gold analytics as JSON for dashboards, mobile apps, or integration.

## Power BI

Gold CSV layer is denormalized and clean — direct import without Spark/SQL knowledge.

## Docker

Packages API + PostgreSQL for reproducible deployment and demo environments.

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Time-series leakage | Chronological train/test split |
| Missing readings | Median imputation in Silver layer |
| Local Spark setup | `local[*]` master + Java requirement documented |
| Power BI compatibility | CSV Gold exports with business column names |
