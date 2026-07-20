from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eligibilityassessment",
            name="assessment_date",
            field=models.DateField(
                default=timezone.localdate,
            ),
        ),
        migrations.AddField(
            model_name="eligibilityassessment",
            name="profile_snapshot",
            field=models.JSONField(default=dict),
        ),
    ]
