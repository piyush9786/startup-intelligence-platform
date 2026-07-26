"""
ML Engine Models

MLFeatureStore  — Caches pre-computed, normalized ML feature vectors for each
                  StartupProfile so that all models can share a single ETL pass.

MLModelRegistry — Tracks every trained model artifact version, its accuracy
                  metrics, and whether it is the currently active model.
"""
from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class MLFeatureStore(TimeStampedModel):
    """Pre-computed, normalized ML feature vector for a StartupProfile."""

    startup_profile = models.OneToOneField(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="ml_features",
    )
    # Serialized numpy array (list of floats) — all features in order
    feature_vector = models.JSONField(default=list)
    feature_version = models.CharField(max_length=64, default="features-v1")
    # K-Means cluster assignment
    cohort_id = models.IntegerField(null=True, blank=True)
    # Isolation Forest anomaly score (negative means anomalous)
    anomaly_score = models.FloatField(null=True, blank=True)
    is_anomalous = models.BooleanField(default=False)
    # AdaBoost readiness improvement probability (0.0–1.0)
    readiness_improvement_probability = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["cohort_id"]),
            models.Index(fields=["is_anomalous"]),
        ]

    def __str__(self) -> str:
        return f"Features for {self.startup_profile} (cohort={self.cohort_id})"


class MLModelRegistry(TimeStampedModel):
    """Tracks trained model artifact versions and which is active."""

    class ModelType(models.TextChoices):
        KMEANS = "kmeans", "K-Means Cohort Clustering"
        SVM = "svm", "SVM Scheme Success Ranker"
        ADABOOST = "adaboost", "AdaBoost Readiness Predictor"
        ISOLATION_FOREST = "isolation_forest", "Isolation Forest Anomaly Detector"
        RANDOM_FOREST = "random_forest", "Random Forest Capital Forecaster"
        TFIDF = "tfidf", "TF-IDF Hybrid Search Index"
        DBSCAN = "dbscan", "DBSCAN Scheme Deduplicator"

    class Status(models.TextChoices):
        TRAINING = "training", "Training"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
        FAILED = "failed", "Failed"

    model_type = models.CharField(max_length=32, choices=ModelType.choices)
    model_name = models.CharField(max_length=128)
    model_version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRAINING)
    training_sample_count = models.PositiveIntegerField(default=0)
    # Accuracy/metric relevant to the model type (accuracy, silhouette score, etc.)
    primary_metric_name = models.CharField(max_length=64, blank=True)
    primary_metric_value = models.FloatField(null=True, blank=True)
    # Path to the serialized .joblib file (relative to ML_MODELS_DIR)
    artifact_path = models.CharField(max_length=512, blank=True)
    # SHA-256 checksum of the artifact file
    artifact_checksum = models.CharField(max_length=64, blank=True)
    training_metadata = models.JSONField(default=dict, blank=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    production_approved = models.BooleanField(default=False)
    deployment_stage = models.CharField(
        max_length=32,
        choices=[
            ("experimental", "Experimental"),
            ("candidate", "Candidate"),
            ("shadow", "Shadow"),
            ("production", "Production"),
        ],
        default="experimental",
    )
    # Promotion audit trail
    promoted_by = models.CharField(max_length=150, blank=True)
    promoted_at = models.DateTimeField(null=True, blank=True)
    promotion_reason = models.TextField(blank=True)
    replaced_model_version = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["model_type", "-model_version"]
        constraints = [
            models.UniqueConstraint(
                fields=["model_type", "model_version"],
                name="unique_model_type_version",
            ),
            models.UniqueConstraint(
                fields=["model_type", "deployment_stage"],
                condition=models.Q(status="active"),
                name="unique_active_model_per_type",
            ),
        ]
        indexes = [
            models.Index(fields=["model_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.model_name} v{self.model_version} ({self.status})"
