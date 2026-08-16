# API Guide

Base URL: `http://localhost:5000`

## GET /health

```json
{"status": "healthy", "service": "smart-energy-analytics"}
```

## GET /api/summary

Returns total energy, averages, peak, meter count, anomaly count, model metrics.

## POST /api/predict

```json
{
  "records": [{
    "timestamp": "2024-01-01T08:00:00",
    "meter_id": "MTR001",
    "energy_consumption_kwh": 0.25,
    "temperature": 18.5,
    "humidity": 60.0,
    "occupancy": 0.7
  }]
}
```

Response:

```json
{"predictions": [0.248]}
```

## GET /api/predictions?limit=100

Returns stored test-set predictions from Gold layer.

## GET /api/anomalies?limit=100

Returns flagged anomaly records.

## GET /api/meters

Returns meter-level summary statistics.

## GET /api/energy/daily?meter_id=MTR001&limit=500

Returns daily aggregated consumption.
