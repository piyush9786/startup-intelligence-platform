from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("recommendations", "0007_scheme_application_tracker"),
        ("startups", "0015_ml_engine_integration"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("compliance_type", models.CharField(choices=[("dpiit", "DPIIT recognition"), ("udyam", "Udyam registration"), ("gst", "GST registration"), ("fssai", "FSSAI licence"), ("shops_establishment", "Shops and Establishments registration"), ("professional_tax", "Professional tax"), ("import_export", "Import Export Code"), ("trademark", "Trademark"), ("other", "Other")], max_length=40)),
                ("title", models.CharField(max_length=255)),
                ("registration_number", models.CharField(blank=True, max_length=255)),
                ("issuing_authority", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("not_started", "Not started"), ("in_progress", "In progress"), ("active", "Active"), ("rejected", "Rejected"), ("suspended", "Suspended"), ("expired", "Expired")], default="not_started", max_length=24)),
                ("issued_on", models.DateField(blank=True, null=True)),
                ("expires_on", models.DateField(blank=True, null=True)),
                ("renewal_reminder_days", models.PositiveSmallIntegerField(default=30)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compliance_records", to=settings.AUTH_USER_MODEL)),
                ("startup_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compliance_records", to="startups.startupprofile")),
            ],
            options={"ordering": ["expires_on", "title", "id"]},
        ),
        migrations.CreateModel(
            name="ConsultantProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("headline", models.CharField(max_length=255)),
                ("bio", models.TextField(blank=True)),
                ("expertise", models.JSONField(blank=True, default=list)),
                ("languages", models.JSONField(blank=True, default=list)),
                ("states_served", models.JSONField(blank=True, default=list)),
                ("industries", models.JSONField(blank=True, default=list)),
                ("hourly_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("availability", models.CharField(choices=[("available", "Available"), ("limited", "Limited availability"), ("unavailable", "Unavailable")], default="available", max_length=20)),
                ("verification_status", models.CharField(choices=[("unverified", "Unverified"), ("pending", "Pending review"), ("verified", "Verified"), ("suspended", "Suspended")], default="unverified", max_length=20)),
                ("is_public", models.BooleanField(default=False)),
                ("years_experience", models.PositiveSmallIntegerField(default=0)),
                ("sessions_completed", models.PositiveIntegerField(default=0)),
                ("average_rating", models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="consultant_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-verification_status", "user__first_name", "user__username"]},
        ),
        migrations.CreateModel(
            name="FounderVaultDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("category", models.CharField(choices=[("incorporation", "Incorporation"), ("tax", "Tax and finance"), ("compliance", "Compliance"), ("founder", "Founder identity"), ("product", "Product and technology"), ("financial", "Financial statements"), ("application", "Scheme application"), ("contract", "Contract"), ("other", "Other")], default="other", max_length=32)),
                ("original_filename", models.CharField(max_length=500)),
                ("mime_type", models.CharField(max_length=255)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("content_hash", models.CharField(db_index=True, max_length=64)),
                ("storage_key", models.CharField(max_length=1000, unique=True)),
                ("bucket_name", models.CharField(max_length=255)),
                ("expires_on", models.DateField(blank=True, null=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("is_archived", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vault_documents", to=settings.AUTH_USER_MODEL)),
                ("startup_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vault_documents", to="startups.startupprofile")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ApplicationTask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("todo", "To do"), ("in_progress", "In progress"), ("blocked", "Blocked"), ("completed", "Completed")], default="todo", max_length=20)),
                ("due_on", models.DateField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflow_tasks", to="recommendations.schemeapplicationtracker")),
            ],
            options={"ordering": ["sort_order", "due_on", "created_at", "id"]},
        ),
        migrations.CreateModel(
            name="ApplicationStageEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("from_stage", models.CharField(blank=True, max_length=30)),
                ("to_stage", models.CharField(max_length=30)),
                ("note", models.TextField(blank=True)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_events", to="recommendations.schemeapplicationtracker")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="application_stage_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-occurred_at", "-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="compliancerecord",
            index=models.Index(fields=["owner", "startup_profile", "status"], name="startup_comp_owner_status"),
        ),
        migrations.AddIndex(
            model_name="compliancerecord",
            index=models.Index(fields=["startup_profile", "expires_on"], name="startup_comp_expiry"),
        ),
        migrations.AddConstraint(
            model_name="compliancerecord",
            constraint=models.CheckConstraint(condition=models.Q(("issued_on__isnull", True), ("expires_on__isnull", True), ("expires_on__gte", models.F("issued_on")), _connector="OR"), name="startup_comp_dates_valid"),
        ),
        migrations.AddIndex(
            model_name="consultantprofile",
            index=models.Index(fields=["is_public", "verification_status", "availability"], name="startup_consultant_directory"),
        ),
        migrations.AddConstraint(
            model_name="consultantprofile",
            constraint=models.CheckConstraint(condition=models.Q(("average_rating__isnull", True), models.Q(("average_rating__gte", 0), ("average_rating__lte", 5)), _connector="OR"), name="startup_consultant_rating_range"),
        ),
        migrations.AddIndex(
            model_name="foundervaultdocument",
            index=models.Index(fields=["owner", "startup_profile", "is_archived"], name="startup_vault_owner_active"),
        ),
        migrations.AddIndex(
            model_name="foundervaultdocument",
            index=models.Index(fields=["startup_profile", "category"], name="startup_vault_category"),
        ),
        migrations.AddConstraint(
            model_name="foundervaultdocument",
            constraint=models.UniqueConstraint(fields=("owner", "startup_profile", "content_hash"), name="startup_vault_unique_hash"),
        ),
        migrations.AddIndex(
            model_name="applicationtask",
            index=models.Index(fields=["application", "status", "due_on"], name="startup_app_task_status"),
        ),
        migrations.AddIndex(
            model_name="applicationstageevent",
            index=models.Index(fields=["application", "-occurred_at"], name="startup_app_event_latest"),
        ),
    ]
