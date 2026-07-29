import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "startups",
            "0017_consultation_request",
        ),
        (
            "research",
            "0006_research_first_workflow",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="startupadvisorbriefing",
            name="source_research_report",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="advisor_briefing",
                to="research.startupresearchreport",
            ),
        ),
        migrations.AddField(
            model_name="startupadvisorbriefingjob",
            name="source_research_report",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="advisor_generation_job",
                to="research.startupresearchreport",
            ),
        ),
    ]
