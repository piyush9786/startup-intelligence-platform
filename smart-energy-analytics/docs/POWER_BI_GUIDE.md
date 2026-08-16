# Power BI Guide

## Import Gold Files

Import these CSV files from `data/gold/`:

| File | Role |
|------|------|
| gold_energy_daily.csv | Fact — daily consumption |
| gold_energy_hourly.csv | Fact — hourly consumption |
| gold_meter_summary.csv | Dimension — meters |
| gold_energy_predictions.csv | Fact — ML predictions |
| gold_energy_anomalies.csv | Fact — anomalies |
| gold_weather_energy_analysis.csv | Fact — weather analysis |

## Relationships

```
dim_meter[meter_id] 1 -> * gold_energy_daily[meter_id]
dim_meter[meter_id] 1 -> * gold_energy_hourly[meter_id]
dim_meter[meter_id] 1 -> * gold_energy_predictions[meter_id]
dim_meter[meter_id] 1 -> * gold_energy_anomalies[meter_id]
gold_energy_daily[date] -> gold_energy_hourly[date] (optional)
```

## Recommended DAX Measures

```dax
Total Energy (kWh) = SUM(gold_energy_daily[total_energy_kwh])

Avg Daily Consumption = AVERAGE(gold_energy_daily[total_energy_kwh])

Peak Consumption = MAX(gold_energy_daily[peak_energy_kwh])

Anomaly Count = SUM(gold_energy_anomalies[anomaly_flag])

Prediction Accuracy % =
VAR actual = SUM(gold_energy_predictions[actual_energy_kwh])
VAR error = SUM(gold_energy_predictions[abs_prediction_error])
RETURN IF(actual = 0, BLANK(), 1 - DIVIDE(error, actual))

Avg Consumption = AVERAGE(gold_energy_daily[avg_energy_kwh])
```

## Dashboard Pages

### Page 1 — Executive Energy Overview
- KPI cards: Total Energy, Avg Daily, Peak, Anomaly Count
- Line chart: daily consumption trend
- Slicers: Date, Meter, Season

### Page 2 — Consumption Analysis
- Column chart: consumption by weekday
- Line chart: hourly trend
- Scatter: consumption vs temperature

### Page 3 — Meter-Level Analysis
- Bar chart: total energy by meter
- Table: gold_meter_summary
- Slicer: Meter

### Page 4 — Prediction & Forecasting
- Line chart: actual vs predicted
- KPI: Prediction Accuracy %
- Scatter: prediction error

### Page 5 — Anomaly Monitoring
- Bar chart: anomalies by meter
- Table: anomaly details
- KPI: Anomaly Count

## Slicers

Date, Meter, Year, Month, Season, Day type (is_weekend), Weather condition

## Refresh

Re-run pipeline locally, then refresh data in Power BI Desktop (Home > Refresh).

```bash
py scripts/run_pipeline.py --sample
```
