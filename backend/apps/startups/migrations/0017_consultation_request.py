import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("startups", "0016_founder_workspace_operations"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsultationRequest",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("topic", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("preferred_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                            ("scheduled", "Scheduled"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="requested",
                        max_length=20,
                    ),
                ),
                ("consultant_response", models.TextField(blank=True)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                (
                    "consultant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consultation_requests",
                        to="startups.consultantprofile",
                    ),
                ),
                (
                    "founder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consultation_requests_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "startup_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consultation_requests",
                        to="startups.startupprofile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="consultationrequest",
            index=models.Index(
                fields=["founder", "status", "-created_at"],
                name="startup_cons_req_founder",
            ),
        ),
        migrations.AddIndex(
            model_name="consultationrequest",
            index=models.Index(
                fields=["consultant", "status", "-created_at"],
                name="startup_cons_req_expert",
            ),
        ),
        migrations.AddIndex(
            model_name="consultationrequest",
            index=models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_cons_req_startup",
            ),
        ),
    ]
