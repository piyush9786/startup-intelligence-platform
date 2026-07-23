import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0009_embeddingrun"),
        ("schemes", "0002_authorityalias"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VerifiedRuleRevision",
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
                ("manifest_key", models.CharField(max_length=150)),
                ("pilot_key", models.CharField(max_length=100)),
                ("reviewed_at", models.DateTimeField()),
                (
                    "manifest_hash",
                    models.CharField(db_index=True, max_length=64),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "base_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verified_rule_revision_bases",
                        to="schemes.schemeversion",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verified_rule_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "revised_version",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verified_rule_revision",
                        to="schemes.schemeversion",
                    ),
                ),
                (
                    "scheme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verified_rule_revisions",
                        to="schemes.scheme",
                    ),
                ),
                (
                    "source_publication",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verified_rule_revisions",
                        to="knowledge.candidatepublication",
                    ),
                ),
            ],
            options={
                "ordering": ["manifest_key", "pilot_key"],
            },
        ),
        migrations.AddConstraint(
            model_name="verifiedrulerevision",
            constraint=models.UniqueConstraint(
                fields=("manifest_key", "pilot_key"),
                name="unique_verified_rule_revision_manifest_pilot",
            ),
        ),
    ]
