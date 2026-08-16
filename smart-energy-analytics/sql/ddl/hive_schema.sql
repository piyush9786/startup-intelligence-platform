-- Hive-compatible DDL for smart energy analytics

CREATE DATABASE IF NOT EXISTS smart_energy
COMMENT 'Smart Energy Analytics Hive warehouse';

USE smart_energy;

CREATE EXTERNAL TABLE IF NOT EXISTS bronze_energy_readings (
    timestamp STRING,
    meter_id STRING,
    voltage DOUBLE,
    current DOUBLE,
    power_factor DOUBLE,
    active_power_kw DOUBLE,
    reactive_power_kvar DOUBLE,
    energy_consumption_kwh DOUBLE,
    temperature DOUBLE,
    humidity DOUBLE,
    weather_condition STRING,
    occupancy DOUBLE,
    appliance_load DOUBLE,
    hvac_load DOUBLE,
    lighting_load DOUBLE,
    is_anomaly_source STRING,
    anomaly_type_source STRING,
    ingestion_ts TIMESTAMP,
    source_file STRING
)
STORED AS PARQUET
LOCATION '/user/hive/warehouse/smart_energy/bronze_energy_readings';

CREATE EXTERNAL TABLE IF NOT EXISTS silver_energy_readings (
    timestamp TIMESTAMP,
    meter_id STRING,
    voltage DOUBLE,
    current DOUBLE,
    power_factor DOUBLE,
    active_power_kw DOUBLE,
    reactive_power_kvar DOUBLE,
    energy_consumption_kwh DOUBLE,
    temperature DOUBLE,
    humidity DOUBLE,
    weather_condition STRING,
    occupancy DOUBLE,
    appliance_load DOUBLE,
    hvac_load DOUBLE,
    lighting_load DOUBLE,
    date DATE,
    year INT,
    month INT,
    day INT,
    hour INT,
    minute INT,
    day_of_week INT,
    day_name STRING,
    week INT,
    quarter INT,
    is_weekend BOOLEAN,
    season STRING
)
STORED AS PARQUET
LOCATION '/user/hive/warehouse/smart_energy/silver_energy_readings';
