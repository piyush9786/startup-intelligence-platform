import uuid

from django.db import migrations, models


def populate_generation_ids(apps, schema_editor):
    recommendation_model = apps.get_model(
        "recommendations",
        "Recommendation",
    )
    for recommendation in recommendation_model.objects.all().iterator():
        recommendation.generation_id = uuid.uuid4()
        recommendation.save(
            update_fields=["generation_id"],
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "recommendations",
            "0002_eligibilityassessment_assessment_date_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendation",
            name="generation_id",
            field=models.UUIDField(
                db_index=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="recommendation",
            name="ranking_version",
            field=models.CharField(
                default="recommendations-v1",
                max_length=50,
            ),
        ),
        migrations.RunPython(
            populate_generation_ids,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="generation_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
            ),
        ),
        migrations.AlterModelOptions(
            name="recommendation",
            options={
                "ordering": [
                    "startup_profile",
                    "rank",
                ]
            },
        ),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.UniqueConstraint(
                fields=(
                    "generation_id",
                    "rank",
                ),
                name=(
                    "unique_recommendation_generation_rank"
                ),
            ),
        ),
    ]
