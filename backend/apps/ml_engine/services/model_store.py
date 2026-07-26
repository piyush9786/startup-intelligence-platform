"""
Model Store — Joblib persistence for trained ML model artifacts.

Saves models to ML_MODELS_DIR (configurable in Django settings) and
keeps the MLModelRegistry up to date.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import joblib
from django.conf import settings
from django.db import transaction
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
    version: int | None = None,
    training_sample_count: int = 0,
    primary_metric_name: str = "",
    primary_metric_value: float | None = None,
    metadata: dict | None = None,
) -> MLModelRegistry:  # noqa: F821 — imported at call time to avoid circular
    from apps.ml_engine.models import MLModelRegistry

    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = ML_MODELS_DIR / f"tmp_{model_type}_{uuid.uuid4().hex}.joblib"

    # Save candidate artifact to a temporary path first
    joblib.dump(model_obj, temp_path)

    # Validate that the dumped artifact can be loaded cleanly before database promotion
    try:
        joblib.load(temp_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise ValueError(
            f"Saved artifact for '{model_name}' failed load validation: {exc}"
        ) from exc

    meta = metadata or {}
    is_synthetic = meta.get("training_data_source") == "synthetic"
    is_approved = False
    stage = "shadow" if is_synthetic else "candidate"

    with transaction.atomic():
        # Acquire PostgreSQL transaction-level advisory lock using hash of model_type
        # This serializes version allocation even if the table has no rows to select_for_update.
        from django.db import connection
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                # pg_advisory_xact_lock(int, int) accepts two 32-bit integers
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('ml_model_registry'), hashtext(%s))",
                    [model_type]
                )

        # We can also still do select_for_update for safety on existing rows
        existing = list(
            MLModelRegistry.objects.select_for_update().filter(model_type=model_type)
        )

        if version is None:
            max_ver = max([r.model_version for r in existing], default=0)
            version = max_ver + 1

        final_path = _artifact_path(model_name, version)
        temp_path.replace(final_path)

        # Retire previous models of the same deployment stage (e.g. shadow retires shadow)
        MLModelRegistry.objects.filter(
            model_type=model_type, status=MLModelRegistry.Status.ACTIVE, deployment_stage=stage
        ).update(status=MLModelRegistry.Status.RETIRED)

        registry_entry = MLModelRegistry.objects.create(
            model_type=model_type,
            model_name=model_name,
            model_version=version,
            status=MLModelRegistry.Status.ACTIVE,
            training_sample_count=training_sample_count,
            primary_metric_name=primary_metric_name,
            primary_metric_value=primary_metric_value,
            artifact_path=str(final_path),
            training_metadata=meta,
            trained_at=timezone.now(),
            production_approved=is_approved,
            deployment_stage=stage,
        )
    return registry_entry


def load_model(model_type: str) -> Any:
    """Load the latest active model of any stage. (Legacy/Generic loader)"""
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


def load_production_model(model_type: str) -> Any:
    """Load the currently active production-approved model for a given model_type."""
    from apps.ml_engine.models import MLModelRegistry

    entry = (
        MLModelRegistry.objects.filter(
            model_type=model_type,
            status=MLModelRegistry.Status.ACTIVE,
            deployment_stage="production",
            production_approved=True
        )
        .order_by("-model_version")
        .first()
    )
    if entry is None:
        raise FileNotFoundError(
            f"No active production ML model found for type '{model_type}'."
        )
    return joblib.load(entry.artifact_path)


def load_shadow_model(model_type: str) -> Any:
    """Load the currently active shadow or candidate model for testing."""
    from apps.ml_engine.models import MLModelRegistry

    entry = (
        MLModelRegistry.objects.filter(
            model_type=model_type, status=MLModelRegistry.Status.ACTIVE
        )
        .exclude(deployment_stage="production")
        .order_by("-model_version")
        .first()
    )
    if entry is None:
        raise FileNotFoundError(
            f"No active shadow model found for type '{model_type}'."
        )
    return joblib.load(entry.artifact_path)
