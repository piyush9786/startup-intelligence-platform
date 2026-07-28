"""
ML Engine Admin Configuration

Provides rich admin views for monitoring ML model status,
feature store coverage, and anomaly detections.
"""
from django.contrib import admin

from .models import MLFeatureStore, MLModelRegistry


@admin.register(MLModelRegistry)
class MLModelRegistryAdmin(admin.ModelAdmin):
    list_display = [
        "model_name",
        "model_type",
        "model_version",
        "status",
        "training_sample_count",
        "primary_metric_name",
        "primary_metric_value",
        "trained_at",
    ]
    list_filter = ["model_type", "status"]
    ordering = ["model_type", "-model_version"]
    readonly_fields = [
        "model_type",
        "model_name",
        "model_version",
        "status",
        "training_sample_count",
        "primary_metric_name",
        "primary_metric_value",
        "artifact_path",
        "training_metadata",
        "trained_at",
        "created_at",
        "updated_at",
    ]


@admin.register(MLFeatureStore)
class MLFeatureStoreAdmin(admin.ModelAdmin):
    list_display = [
        "startup_profile",
        "cohort_id",
        "anomaly_score",
        "is_anomalous",
        "readiness_improvement_probability",
        "feature_version",
        "updated_at",
    ]
    list_filter = ["is_anomalous", "cohort_id", "feature_version"]
    search_fields = ["startup_profile__startup_name"]
    ordering = ["-updated_at"]
    readonly_fields = [
        "startup_profile",
        "feature_vector",
        "feature_version",
        "cohort_id",
        "anomaly_score",
        "is_anomalous",
        "readiness_improvement_probability",
        "created_at",
        "updated_at",
    ]
