"""Run complete Smart Energy Analytics pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anomaly_detection.detector import detect_anomalies
from src.ingestion.data_generator import generate_dataset
from src.ml.train import train_models
from src.processing.spark_pipeline import run_pipeline
from src.utils.config_loader import setup_logging

logger = setup_logging("run_pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run end-to-end smart energy pipeline")
    parser.add_argument("--sample", action="store_true", help="Use sample dataset size")
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()

    if not args.skip_generate:
        logger.info("Phase 1: Generating data...")
        generate_dataset(sample=args.sample)

    logger.info("Phase 2: Running PySpark pipeline...")
    run_pipeline()

    logger.info("Phase 3: Training ML models...")
    train_models()

    logger.info("Phase 3: Detecting anomalies...")
    detect_anomalies()

    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
