import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("startups", "0002_startupreadinessassessment"),
    ]

    operations = [
        migrations.CreateModel(
            name="StartupReadinessActionPlan",
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
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "source_assessment_snapshot",
                    models.JSONField(default=dict),
                ),
                (
                    "readiness_status",
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
                ("has_actions", models.BooleanField()),
                (
                    "blocker_count",
                    models.PositiveIntegerField(),
                ),
                (
                    "recommendation_count",
                    models.PositiveIntegerField(),
                ),
                (
                    "total_action_count",
                    models.PositiveIntegerField(),
                ),
                (
                    "next_action",
                    models.TextField(blank=True, null=True),
                ),
                ("items", models.JSONField(default=list)),
                (
                    "source_engine_version",
                    models.CharField(max_length=64),
                ),
                (
                    "planner_version",
                    models.CharField(max_length=64),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="startup_readiness_action_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="action_plans",
                        to="startups.startupreadinessassessment",
                    ),
                ),
                (
                    "startup_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="readiness_action_plans",
                        to="startups.startupprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=["startup_profile", "-created_at"],
                        name="startup_action_profile_created",
                    ),
                    models.Index(
                        fields=["source_assessment", "-created_at"],
                        name="startup_action_source_created",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                has_actions=True,
                                total_action_count__gt=0,
                                next_action__isnull=False,
                            )
                            | models.Q(
                                has_actions=False,
                                total_action_count=0,
                                next_action__isnull=True,
                            )
                        ),
                        name="startup_action_presence_match",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            total_action_count=(
                                models.F("blocker_count")
                                + models.F("recommendation_count")
                            ),
                        ),
                        name="startup_action_counts_match",
                    ),
                ],
            },
        ),
    ]
