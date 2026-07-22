import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
        ("knowledge", "0008_externalknowledgedataset_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmbeddingRun",
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
                (
                    "provider",
                    models.CharField(
                        default="ollama",
                        max_length=64,
                    ),
                ),
                ("model_name", models.CharField(max_length=255)),
                (
                    "embedding_version",
                    models.CharField(max_length=64),
                ),
                (
                    "collection_name",
                    models.CharField(max_length=255),
                ),
                (
                    "vector_size",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "chunk_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "embedded_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "finished_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("error_message", models.TextField(blank=True)),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "extraction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding_runs",
                        to="documents.documentextraction",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="embeddingrun",
            constraint=models.UniqueConstraint(
                fields=(
                    "extraction",
                    "model_name",
                    "embedding_version",
                ),
                name="unique_embedding_run_version",
            ),
        ),
        migrations.AddIndex(
            model_name="embeddingrun",
            index=models.Index(
                fields=["status", "-created_at"],
                name="knowledge_e_status_6d40ef_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="embeddingrun",
            index=models.Index(
                fields=["model_name", "embedding_version"],
                name="knowledge_e_model_n_314329_idx",
            ),
        ),
    ]
