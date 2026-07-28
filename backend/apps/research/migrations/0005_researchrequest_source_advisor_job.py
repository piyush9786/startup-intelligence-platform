from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("research", "0004_researchrequest_source_advisor_briefing"),
        ("startups", "0008_startupassessmentdraft_race_hardening"),
    ]

    operations = [
        migrations.AddField(
            model_name="researchrequest",
            name="source_advisor_job",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="automatic_research_request",
                to="startups.startupadvisorbriefingjob",
            ),
        ),
    ]
