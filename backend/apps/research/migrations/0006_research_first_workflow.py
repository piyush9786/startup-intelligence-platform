import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "research",
            "0005_researchrequest_source_advisor_job",
        ),
        (
            "startups",
            "0017_consultation_request",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="researchrequest",
            name="workflow_type",
            field=models.CharField(
                choices=[
                    (
                        "standalone",
                        "Standalone research",
                    ),
                    (
                        "advisor_followup",
                        "Advisor follow-up research",
                    ),
                    (
                        "research_first_intelligence",
                        "Research-first founder intelligence",
                    ),
                ],
                db_index=True,
                default="standalone",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="researchrequest",
            name="advisor_snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="research_first_requests",
                to="startups.startupadvisorsnapshot",
            ),
        ),
    ]
