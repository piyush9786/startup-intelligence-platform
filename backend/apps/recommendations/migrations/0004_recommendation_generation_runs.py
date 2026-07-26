import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import Count, Max, Min, Q


def backfill_generation_runs(apps, schema_editor):
    recommendation_model = apps.get_model(
        "recommendations",
        "Recommendation",
    )
    assessment_model = apps.get_model(
        "recommendations",
        "EligibilityAssessment",
    )
    run_model = apps.get_model(
        "recommendations",
        "RecommendationGenerationRun",
    )

    groups = (
        recommendation_model.objects.values(
            "startup_profile_id",
            "generation_id",
            "ranking_version",
        )
        .annotate(
            recommendation_count=Count("id"),
            first_created=Min("created_at"),
            last_updated=Max("updated_at"),
        )
        .order_by(
            "startup_profile_id",
            "first_created",
            "generation_id",
        )
    )

    latest_run_by_profile = {}

    for group in groups:
        recommendations = list(
            recommendation_model.objects.filter(
                startup_profile_id=(
                    group["startup_profile_id"]
                ),
                generation_id=group["generation_id"],
                ranking_version=group["ranking_version"],
            )
            .select_related(
                "assessment",
                "scheme_version",
            )
            .order_by("rank", "id")
        )
        if not recommendations:
            continue

        first = recommendations[0]
        first_assessment = first.assessment
        snapshot = []
        assessment_ids = []

        for recommendation in recommendations:
            assessment_ids.append(
                recommendation.assessment_id,
            )
            snapshot.append(
                {
                    "recommendation_id": str(
                        recommendation.id,
                    ),
                    "assessment_id": str(
                        recommendation.assessment_id,
                    ),
                    "scheme_version_id": str(
                        recommendation.scheme_version_id,
                    ),
                    "rank": recommendation.rank,
                    "score": format(
                        recommendation.score,
                        "f",
                    ),
                    "score_breakdown": (
                        recommendation.score_breakdown
                    ),
                    "evidence_snapshot": (
                        recommendation.evidence_snapshot
                    ),
                }
            )

        run = run_model.objects.create(
            id=group["generation_id"],
            requested_by_id=(
                first_assessment.requested_by_id
            ),
            startup_profile_id=(
                group["startup_profile_id"]
            ),
            assessment_date=(
                first_assessment.assessment_date
            ),
            ranking_version=group["ranking_version"],
            profile_snapshot=(
                first_assessment.profile_snapshot
            ),
            assessed_scheme_count=(
                group["recommendation_count"]
            ),
            recommendation_count=(
                group["recommendation_count"]
            ),
            excluded_schemes=[],
            recommendation_snapshot=snapshot,
            is_current=False,
            completed_at=group["first_created"],
        )

        run_model.objects.filter(pk=run.pk).update(
            created_at=group["first_created"],
            updated_at=group["last_updated"],
        )
        recommendation_model.objects.filter(
            id__in=[
                item.id
                for item in recommendations
            ]
        ).update(
            generation_run_id=run.id,
        )
        assessment_model.objects.filter(
            id__in=assessment_ids,
            generation_run_id__isnull=True,
        ).update(
            generation_run_id=run.id,
        )

        profile_id = group["startup_profile_id"]
        latest = latest_run_by_profile.get(profile_id)
        candidate = (
            group["first_created"],
            str(run.id),
            run.id,
        )
        if latest is None or candidate > latest:
            latest_run_by_profile[profile_id] = candidate

    for _, _, run_id in latest_run_by_profile.values():
        run_model.objects.filter(pk=run_id).update(
            is_current=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "recommendations",
            "0003_recommendation_generation_metadata",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationGenerationRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=__import__("uuid").uuid4,
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
                    "ranking_version",
                    models.CharField(
                        default="recommendations-v1",
                        max_length=50,
                    ),
                ),
                (
                    "profile_snapshot",
                    models.JSONField(default=dict),
                ),
                (
                    "assessed_scheme_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "recommendation_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "excluded_schemes",
                    models.JSONField(default=list),
                ),
                (
                    "recommendation_snapshot",
                    models.JSONField(default=list),
                ),
                (
                    "is_current",
                    models.BooleanField(default=True),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
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
                            "recommendation_generation_runs"
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
                        related_name=(
                            "recommendation_generation_runs"
                        ),
                        to="startups.startupprofile",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "startup_profile",
                    "-completed_at",
                    "-created_at",
                ],
            },
        ),
        migrations.AddField(
            model_name="eligibilityassessment",
            name="generation_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assessments",
                to=(
                    "recommendations."
                    "recommendationgenerationrun"
                ),
            ),
        ),
        migrations.AddField(
            model_name="recommendation",
            name="generation_run",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="recommendations",
                to=(
                    "recommendations."
                    "recommendationgenerationrun"
                ),
            ),
        ),
        migrations.RunPython(
            backfill_generation_runs,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="generation_run",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="recommendations",
                to=(
                    "recommendations."
                    "recommendationgenerationrun"
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="recommendationgenerationrun",
            constraint=models.UniqueConstraint(
                condition=Q(is_current=True),
                fields=("startup_profile",),
                name="unique_current_recommendation_run",
            ),
        ),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.UniqueConstraint(
                fields=(
                    "generation_run",
                    "rank",
                ),
                name="unique_recommendation_run_rank",
            ),
        ),
    ]
