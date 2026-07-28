"""
Celery tasks for the ML Engine.

Scheduled jobs:
  - nightly_feature_extraction: Extract + cache features for all StartupProfiles
  - nightly_anomaly_and_cohort: Run Isolation Forest + K-Means on all profiles
  - weekly_model_retraining: Re-train all 7 models with latest data
  - on_demand_scheme_dedup: Run DBSCAN dedup on new scheme embeddings from Qdrant
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="ml_engine.nightly_feature_extraction")
def nightly_feature_extraction():
    """
    Nightly ETL: Extract and cache ML feature vectors for all StartupProfiles.
    Creates/updates MLFeatureStore entries.
    """
    from apps.ml_engine.models import MLFeatureStore
    from apps.ml_engine.services.feature_pipeline import extract_features
    from apps.startups.models import StartupProfile

    profiles = StartupProfile.objects.prefetch_related("readiness_assessments", "recommendations")
    updated = 0
    for profile in profiles:
        vec = extract_features(profile)
        MLFeatureStore.objects.update_or_create(
            startup_profile=profile,
            defaults={
                "feature_vector": vec.tolist(),
                "feature_version": "features-v1",
            },
        )
        updated += 1

    logger.info("nightly_feature_extraction: updated %d feature store entries", updated)
    return {"updated": updated}


@shared_task(name="ml_engine.nightly_anomaly_and_cohort")
def nightly_anomaly_and_cohort():
    """
    Nightly ML inference:
    1. Run Isolation Forest to score all profiles for anomalies.
    2. Run K-Means to assign/update cohort IDs.
    """
    from apps.ml_engine.services.models.isolation_forest_detector import score_anomaly
    from apps.ml_engine.services.models.kmeans_cohorts import assign_cohort
    from apps.startups.models import StartupProfile

    profiles = StartupProfile.objects.all()
    anomaly_flagged = 0
    for profile in profiles:
        try:
            score, is_anomalous = score_anomaly(profile)
            cohort = assign_cohort(profile)
            profile.ml_cohort_id = cohort
            profile.anomaly_score = score
            profile.is_anomalous = is_anomalous
            profile.save(update_fields=["ml_cohort_id", "anomaly_score", "is_anomalous"])
            if is_anomalous:
                anomaly_flagged += 1
        except Exception as exc:
            logger.warning("Failed ML inference for profile %s: %s", profile.pk, exc)

    logger.info("nightly_anomaly_and_cohort: anomaly_flagged=%d", anomaly_flagged)
    return {"anomaly_flagged": anomaly_flagged, "total": profiles.count()}


@shared_task(name="ml_engine.weekly_model_retraining")
def weekly_model_retraining():
    """
    Weekly re-training of all scikit-learn models using the latest data.
    Falls back to synthetic data if fewer than 50 real profiles exist.
    """
    import subprocess
    import sys

    logger.info("Starting weekly ML model re-training...")
    result = subprocess.run(
        [sys.executable, "manage.py", "train_ml_models"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("ML retraining failed: %s", result.stderr)
        raise RuntimeError(f"ML retraining failed: {result.stderr}")

    logger.info("Weekly model retraining completed successfully.")
    return {"status": "success"}


@shared_task(name="ml_engine.on_demand_scheme_dedup")
def on_demand_scheme_dedup():
    """
    Run DBSCAN deduplication on scheme embeddings stored in Qdrant.
    Logs any duplicate groups found for admin review.
    """
    from django.conf import settings

    from apps.knowledge.services.vector_search import get_qdrant_client
    from apps.ml_engine.services.models.dbscan_dedup import find_duplicate_schemes

    try:
        client = get_qdrant_client()
        collection = settings.STARTUP_ADVISOR_QDRANT_COLLECTION

        # Scroll all points from Qdrant
        points, _ = client.scroll(
            collection_name=collection,
            with_vectors=True,
            limit=2000,
        )
        scheme_embeddings = [
            {
                "scheme_version_id": str(p.payload.get("scheme_version_id", p.id)),
                "vector": p.vector,
            }
            for p in points
            if p.vector
        ]

        result = find_duplicate_schemes(scheme_embeddings)
        if result["duplicate_groups"]:
            logger.warning(
                "DBSCAN found %d duplicate scheme groups: %s",
                len(result["duplicate_groups"]),
                result["duplicate_groups"][:5],
            )
        return {
            "duplicate_groups": len(result["duplicate_groups"]),
            "unique_count": result["unique_count"],
        }
    except Exception as exc:
        logger.error("on_demand_scheme_dedup failed: %s", exc)
        return {"error": str(exc)}
