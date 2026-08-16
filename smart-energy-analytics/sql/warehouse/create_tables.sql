-- PostgreSQL warehouse schema for Smart Energy Analytics

CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(15) NOT NULL,
    week INT NOT NULL,
    quarter INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    season VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_meter (
    meter_id VARCHAR(20) PRIMARY KEY,
    first_reading_date DATE,
    last_reading_date DATE,
    total_readings INT,
    avg_energy_kwh NUMERIC(12, 6),
    peak_energy_kwh NUMERIC(12, 6)
);

CREATE TABLE IF NOT EXISTS dim_weather (
    weather_key SERIAL PRIMARY KEY,
    weather_condition VARCHAR(20) NOT NULL,
    season VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_energy_consumption (
    consumption_id BIGSERIAL PRIMARY KEY,
    date_key DATE REFERENCES dim_date(date_key),
    meter_id VARCHAR(20) REFERENCES dim_meter(meter_id),
    total_energy_kwh NUMERIC(14, 6) NOT NULL,
    avg_energy_kwh NUMERIC(12, 6),
    peak_energy_kwh NUMERIC(12, 6),
    avg_temperature NUMERIC(8, 2),
    avg_humidity NUMERIC(8, 2),
    reading_count INT
);

CREATE TABLE IF NOT EXISTS fact_energy_prediction (
    prediction_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    meter_id VARCHAR(20) REFERENCES dim_meter(meter_id),
    actual_energy_kwh NUMERIC(12, 6),
    predicted_energy_kwh NUMERIC(12, 6),
    prediction_error NUMERIC(12, 6),
    abs_prediction_error NUMERIC(12, 6)
);

CREATE TABLE IF NOT EXISTS fact_energy_anomaly (
    anomaly_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    meter_id VARCHAR(20) REFERENCES dim_meter(meter_id),
    energy_consumption_kwh NUMERIC(12, 6),
    anomaly_flag INT NOT NULL,
    anomaly_score NUMERIC(10, 6),
    anomaly_reason VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_fact_energy_date ON fact_energy_consumption(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_energy_meter ON fact_energy_consumption(meter_id);
CREATE INDEX IF NOT EXISTS idx_fact_anomaly_meter ON fact_energy_anomaly(meter_id);
CREATE INDEX IF NOT EXISTS idx_fact_prediction_meter ON fact_energy_prediction(meter_id);
