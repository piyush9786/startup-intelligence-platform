"""PySpark medallion pipeline: RAW -> BRONZE -> SILVER -> GOLD."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from src.utils.config_loader import ensure_dir, load_config, resolve_path, setup_logging

logger = setup_logging(__name__)

RAW_SCHEMA = StructType(
    [
        StructField("timestamp", StringType(), True),
        StructField("meter_id", StringType(), True),
        StructField("voltage", DoubleType(), True),
        StructField("current", DoubleType(), True),
        StructField("power_factor", DoubleType(), True),
        StructField("active_power_kw", DoubleType(), True),
        StructField("reactive_power_kvar", DoubleType(), True),
        StructField("energy_consumption_kwh", DoubleType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("weather_condition", StringType(), True),
        StructField("occupancy", DoubleType(), True),
        StructField("appliance_load", DoubleType(), True),
        StructField("hvac_load", DoubleType(), True),
        StructField("lighting_load", DoubleType(), True),
        StructField("is_anomaly_source", StringType(), True),
        StructField("anomaly_type_source", StringType(), True),
    ]
)


def create_spark(app_name: str, master: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.warehouse.dir", str(resolve_path("spark-warehouse")))
        .getOrCreate()
    )


def _find_input_csv(raw_dir: Path, sample_dir: Path) -> Path:
    for directory in (raw_dir, sample_dir):
        candidate = directory / "smart_meter_readings.csv"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No smart_meter_readings.csv found in data/raw or data/sample")


def run_bronze(spark: SparkSession, input_csv: Path, bronze_dir: Path):
    logger.info("Running BRONZE layer from %s", input_csv)
    df = (
        spark.read.option("header", True)
        .schema(RAW_SCHEMA)
        .csv(str(input_csv))
        .withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("source_file", F.lit(input_csv.name))
    )
    bronze_path = bronze_dir / "bronze_energy_readings"
    df.write.mode("overwrite").parquet(str(bronze_path))
    return df, bronze_path


def run_silver(spark: SparkSession, bronze_path: Path, silver_dir: Path):
    logger.info("Running SILVER layer")
    df = spark.read.parquet(str(bronze_path))

    df = df.withColumn("timestamp", F.to_timestamp("timestamp"))
    df = df.dropDuplicates(["meter_id", "timestamp"])
    df = df.filter(F.col("timestamp").isNotNull())
    df = df.filter(
        (F.col("energy_consumption_kwh") >= 0)
        & (F.col("energy_consumption_kwh") <= 50)
        & (F.col("voltage").between(180, 260))
        & (F.col("power_factor").between(0.5, 1.0))
    )

    numeric_cols = [
        "voltage",
        "current",
        "power_factor",
        "active_power_kw",
        "reactive_power_kvar",
        "energy_consumption_kwh",
        "temperature",
        "humidity",
        "occupancy",
        "appliance_load",
        "hvac_load",
        "lighting_load",
    ]
    for col_name in numeric_cols:
        median_val = df.approxQuantile(col_name, [0.5], 0.01)[0]
        df = df.withColumn(
            col_name,
            F.when(F.col(col_name).isNull(), F.lit(median_val)).otherwise(F.col(col_name)),
        )

    df = (
        df.withColumn("date", F.to_date("timestamp"))
        .withColumn("year", F.year("timestamp"))
        .withColumn("month", F.month("timestamp"))
        .withColumn("day", F.dayofmonth("timestamp"))
        .withColumn("hour", F.hour("timestamp"))
        .withColumn("minute", F.minute("timestamp"))
        .withColumn("day_of_week", F.dayofweek("timestamp"))
        .withColumn(
            "day_name",
            F.date_format("timestamp", "EEEE"),
        )
        .withColumn("week", F.weekofyear("timestamp"))
        .withColumn("quarter", F.quarter("timestamp"))
        .withColumn("is_weekend", F.when(F.col("day_of_week").isin(1, 7), True).otherwise(False))
        .withColumn(
            "season",
            F.when(F.col("month").isin(12, 1, 2), "winter")
            .when(F.col("month").isin(3, 4, 5), "spring")
            .when(F.col("month").isin(6, 7, 8), "summer")
            .otherwise("autumn"),
        )
    )

    silver_path = silver_dir / "silver_energy_readings"
    df.write.mode("overwrite").parquet(str(silver_path))
    return df, silver_path


def run_gold(spark: SparkSession, silver_path: Path, gold_dir: Path) -> dict[str, Path]:
    logger.info("Running GOLD layer")
    ensure_dir(gold_dir)
    df = spark.read.parquet(str(silver_path))

    daily = (
        df.groupBy("date", "meter_id", "year", "month", "day", "day_name", "day_of_week", "is_weekend", "season")
        .agg(
            F.sum("energy_consumption_kwh").alias("total_energy_kwh"),
            F.avg("energy_consumption_kwh").alias("avg_energy_kwh"),
            F.max("energy_consumption_kwh").alias("peak_energy_kwh"),
            F.avg("temperature").alias("avg_temperature"),
            F.avg("humidity").alias("avg_humidity"),
            F.avg("occupancy").alias("avg_occupancy"),
            F.count("*").alias("reading_count"),
        )
        .orderBy("date", "meter_id")
    )

    hourly = (
        df.groupBy(
            "date",
            "hour",
            "meter_id",
            "year",
            "month",
            "day_name",
            "is_weekend",
            "season",
        )
        .agg(
            F.sum("energy_consumption_kwh").alias("total_energy_kwh"),
            F.avg("energy_consumption_kwh").alias("avg_energy_kwh"),
            F.max("active_power_kw").alias("peak_power_kw"),
            F.avg("temperature").alias("avg_temperature"),
            F.avg("occupancy").alias("avg_occupancy"),
        )
        .orderBy("date", "hour", "meter_id")
    )

    meter_summary = (
        df.groupBy("meter_id")
        .agg(
            F.sum("energy_consumption_kwh").alias("total_energy_kwh"),
            F.avg("energy_consumption_kwh").alias("avg_energy_kwh"),
            F.max("energy_consumption_kwh").alias("peak_energy_kwh"),
            F.stddev("energy_consumption_kwh").alias("std_energy_kwh"),
            F.avg("temperature").alias("avg_temperature"),
            F.count("*").alias("total_readings"),
            F.min("date").alias("first_reading_date"),
            F.max("date").alias("last_reading_date"),
        )
        .orderBy("meter_id")
    )

    weather_analysis = (
        df.groupBy("weather_condition", "season", "is_weekend")
        .agg(
            F.sum("energy_consumption_kwh").alias("total_energy_kwh"),
            F.avg("energy_consumption_kwh").alias("avg_energy_kwh"),
            F.avg("temperature").alias("avg_temperature"),
            F.count("*").alias("reading_count"),
        )
        .orderBy("weather_condition", "season")
    )

    outputs: dict[str, Path] = {}
    gold_files = {
        "gold_energy_daily": daily,
        "gold_energy_hourly": hourly,
        "gold_meter_summary": meter_summary,
        "gold_weather_energy_analysis": weather_analysis,
    }

    for name, frame in gold_files.items():
        csv_path = gold_dir / f"{name}.csv"
        parquet_path = gold_dir / f"{name}.parquet"
        frame.coalesce(1).write.mode("overwrite").option("header", True).csv(str(gold_dir / f"_{name}_csv"))
        frame.write.mode("overwrite").parquet(str(parquet_path))

        part_files = list((gold_dir / f"_{name}_csv").glob("part-*.csv"))
        if part_files:
            part_files[0].replace(csv_path)
        outputs[name] = csv_path

    silver_csv = gold_dir / "silver_for_ml.csv"
    df.select(
        "timestamp",
        "meter_id",
        "energy_consumption_kwh",
        "temperature",
        "humidity",
        "occupancy",
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "season",
        "weather_condition",
        "active_power_kw",
        "hvac_load",
        "lighting_load",
        "appliance_load",
        "is_anomaly_source",
        "anomaly_type_source",
    ).coalesce(1).write.mode("overwrite").option("header", True).csv(str(gold_dir / "_silver_csv"))
    part = list((gold_dir / "_silver_csv").glob("part-*.csv"))
    if part:
        part[0].replace(silver_csv)
    outputs["silver_for_ml"] = silver_csv

    return outputs


def run_pipeline(config_path: str | None = None) -> dict[str, Path]:
    try:
        import pyspark  # noqa: F401
    except ImportError:
        logger.warning("PySpark not installed; using pandas fallback pipeline.")
        from src.processing.pandas_pipeline import run_pipeline_pandas

        return run_pipeline_pandas(config_path=config_path)

    cfg = load_config(Path(config_path) if config_path else None)
    paths = cfg["paths"]
    proc = cfg["processing"]

    raw_dir = ensure_dir(resolve_path(paths["raw"]))
    sample_dir = ensure_dir(resolve_path("data/sample"))
    bronze_dir = ensure_dir(resolve_path(paths["bronze"]))
    silver_dir = ensure_dir(resolve_path(paths["silver"]))
    gold_dir = ensure_dir(resolve_path(paths["gold"]))

    input_csv = _find_input_csv(raw_dir, sample_dir)
    spark = create_spark(proc["app_name"], proc["spark_master"])

    try:
        _, bronze_path = run_bronze(spark, input_csv, bronze_dir)
        _, silver_path = run_silver(spark, bronze_path, silver_dir)
        outputs = run_gold(spark, silver_path, gold_dir)
    finally:
        spark.stop()

    logger.info("Pipeline complete. Gold outputs: %s", list(outputs.keys()))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PySpark medallion pipeline")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    run_pipeline(config_path=args.config)


if __name__ == "__main__":
    main()
