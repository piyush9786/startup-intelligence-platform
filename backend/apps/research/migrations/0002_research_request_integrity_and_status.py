from django.db import migrations, models
from django.db.models import Count
from django.utils import timezone


def resolve_duplicate_active_requests(apps, schema_editor):
    ResearchRequest = apps.get_model("research", "ResearchRequest")
    duplicate_profiles = (
        ResearchRequest.objects.filter(status__in=["queued", "running"])
        .values("startup_profile_id")
        .annotate(active_count=Count("id"))
        .filter(active_count__gt=1)
    )
    for duplicate in duplicate_profiles.iterator():
        active_requests = ResearchRequest.objects.filter(
            startup_profile_id=duplicate["startup_profile_id"],
            status__in=["queued", "running"],
        ).order_by("created_at", "id")
        keep_id = active_requests.values_list("id", flat=True).first()
        active_requests.exclude(id=keep_id).update(
            status="failed",
            completed_at=timezone.now(),
            error_code="duplicate_active_job",
            error_message=(
                "Closed while adding the one-active-research-job constraint."
            ),
        )


class Migration(migrations.Migration):

    dependencies = [
        ("research", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="researchrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("succeeded", "Succeeded"),
                    ("partial", "Partial results"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                default="queued",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="researchsearchquery",
            name="error_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="researchsearchquery",
            name="status",
            field=models.CharField(
                choices=[
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                ],
                default="succeeded",
                max_length=16,
            ),
        ),
        migrations.RunPython(
            resolve_duplicate_active_requests,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="researchrequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["queued", "running"]),
                fields=("startup_profile",),
                name="research_one_active_request_per_profile",
            ),
        ),
    ]
