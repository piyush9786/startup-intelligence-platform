"""
Model Store — Joblib persistence for trained ML model artifacts.

Saves models to ML_MODELS_DIR (configurable in Django settings) and
keeps the MLModelRegistry up to date.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from django.conf import settings
from django.utils import timezone

ML_MODELS_DIR = Path(getattr(settings, "ML_MODELS_DIR", "/app/ml_models"))


def _artifact_path(model_name: str, version: int) -> Path:
    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return ML_MODELS_DIR / f"{model_name}_v{version}.joblib"


def save_model(
    *,
    model_type: str,
    model_name: str,
    model_obj: Any,
    version: int,
    training_sample_count: int = 0,
    primary_metric_name: str = "",
    primary_metric_value: float | None = None,
    metadata: dict | None = None,
) -> MLModelRegistry:  # noqa: F821 — imported at call time to avoid circular
    from django.db import transaction

    from apps.ml_engine.models import MLModelRegistry

    path = _artifact_path(model_name, version)
    
    # Save candidate artifact to storage
    joblib.dump(model_obj, path)

    with transaction.atomic():
        # Acquire a database lock on the active model of this type to prevent concurrent promotion races
        active_models = MLModelRegistry.objects.select_for_update().filter(
            model_type=model_type, status=MLModelRegistry.Status.ACTIVE
        )
        
        # Retire previous active model of the same type
        active_models.update(status=MLModelRegistry.Status.RETIRED)

        registry_entry = MLModelRegistry.objects.create(
            model_type=model_type,
            model_name=model_name,
            model_version=version,
            status=MLModelRegistry.Status.ACTIVE,
            training_sample_count=training_sample_count,
            primary_metric_name=primary_metric_name,
            primary_metric_value=primary_metric_value,
            artifact_path=str(path),
            training_metadata=metadata or {},
            trained_at=timezone.now(),
        )
    return registry_entry


def load_model(model_type: str) -> Any:
    """Load the currently active model for a given model_type."""
    from apps.ml_engine.models import MLModelRegistry

    entry = (
        MLModelRegistry.objects.filter(
            model_type=model_type, status=MLModelRegistry.Status.ACTIVE
        )
        .order_by("-model_version")
        .first()
    )
    if entry is None:
        raise FileNotFoundError(
            f"No active ML model found for type '{model_type}'. "
            "Run 'python manage.py train_ml_models' first."
        )
    return joblib.load(entry.artifact_path)


def next_version(model_type: str) -> int:
    """Return the next available version number for a model type."""
    from apps.ml_engine.models import MLModelRegistry

    latest = (
        MLModelRegistry.objects.filter(model_type=model_type)
        .order_by("-model_version")
        .values_list("model_version", flat=True)
        .first()
    )
    return (latest or 0) + 1
