import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
        ("startups", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StartupReadinessAssessment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
                (
                    "assessment_date",
                    models.DateField(),
                ),
                (
                    "profile_snapshot",
                    models.JSONField(
                        default=dict,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("blocked", "Blocked"),
                            (
                                "ready_with_recommendations",
                                "Ready with recommendations",
                            ),
                            ("ready", "Ready"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "score",
                    models.PositiveSmallIntegerField(),
                ),
                (
                    "critical_score",
                    models.PositiveSmallIntegerField(),
                ),
                (
                    "recommended_score",
                    models.PositiveSmallIntegerField(),
                ),
                (
                    "findings",
                    models.JSONField(
                        default=list,
                    ),
                ),
                (
                    "blocking_findings",
                    models.JSONField(
                        default=list,
                    ),
                ),
                (
                    "summary",
                    models.TextField(),
                ),
                (
                    "engine_version",
                    models.CharField(
                        max_length=64,
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=(
                            django.db.models.deletion.SET_NULL
                        ),
                        related_name=(
                            "startup_readiness_assessments"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "startup_profile",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name="readiness_assessments",
                        to="startups.startupprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=[
                            "startup_profile",
                            "-created_at",
                        ],
                        name=(
                            "startup_ready_profile_created"
                        ),
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            score__gte=0,
                            score__lte=100,
                            critical_score__gte=0,
                            critical_score__lte=100,
                            recommended_score__gte=0,
                            recommended_score__lte=100,
                        ),
                        name="startup_ready_scores_range",
                    ),
                ],
            },
        ),
    ]
