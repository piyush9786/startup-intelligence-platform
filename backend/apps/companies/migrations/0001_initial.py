import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
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
                ("canonical_name", models.CharField(max_length=255)),
                (
                    "normalized_name",
                    models.CharField(db_index=True, editable=False, max_length=255),
                ),
                ("industry", models.CharField(max_length=150)),
                ("sub_industry", models.CharField(blank=True, max_length=150)),
                ("business_model", models.CharField(max_length=100)),
                ("customer_segment", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("founded_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("website", models.URLField(blank=True, max_length=1000)),
                (
                    "operating_status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("profitable", "Profitable"),
                            ("acquired", "Acquired"),
                            ("merged", "Merged"),
                            ("ipo", "IPO"),
                            ("pivoted", "Pivoted"),
                            ("closed", "Closed"),
                            ("inactive", "Inactive"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("unverified", "Unverified"),
                            ("partially_verified", "Partially verified"),
                            ("verified", "Verified"),
                            ("disputed", "Disputed"),
                        ],
                        default="unverified",
                        max_length=24,
                    ),
                ),
            ],
            options={
                "ordering": ["canonical_name"],
                "indexes": [
                    models.Index(
                        fields=["industry", "business_model", "country"],
                        name="company_peer_lookup_idx",
                    ),
                    models.Index(
                        fields=["operating_status", "verification_status"],
                        name="company_status_verify_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="CompanyDataSource",
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
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("government", "Government data"),
                            ("public_dataset", "Public dataset"),
                            ("company_disclosure", "Company disclosure"),
                            ("research_report", "Research report"),
                            ("news", "News"),
                            ("manual", "Manual research"),
                        ],
                        max_length=32,
                    ),
                ),
                ("publisher", models.CharField(blank=True, max_length=255)),
                ("source_url", models.URLField(blank=True, max_length=1500)),
                ("licence", models.CharField(blank=True, max_length=255)),
                (
                    "reliability_score",
                    models.DecimalField(
                        decimal_places=3,
                        help_text=(
                            "Governance score from 0 (untrusted) to 1 "
                            "(highest confidence)."
                        ),
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending review"),
                            ("reviewed", "Reviewed"),
                            ("verified", "Verified"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                ("last_retrieved_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="RawCompanyDataset",
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
                ("dataset_id", models.CharField(max_length=150, unique=True)),
                ("original_filename", models.CharField(max_length=500)),
                ("original_url", models.URLField(blank=True, max_length=1500)),
                ("storage_path", models.CharField(blank=True, max_length=1500)),
                (
                    "checksum_sha256",
                    models.CharField(db_index=True, max_length=64),
                ),
                ("content_length", models.PositiveBigIntegerField(default=0)),
                ("retrieved_at", models.DateTimeField()),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                (
                    "parsing_status",
                    models.CharField(
                        choices=[
                            ("registered", "Registered"),
                            ("processing", "Processing"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                        ],
                        default="registered",
                        max_length=20,
                    ),
                ),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("accepted_count", models.PositiveIntegerField(default=0)),
                ("rejected_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="datasets",
                        to="companies.companydatasource",
                    ),
                ),
            ],
            options={
                "ordering": ["-retrieved_at", "-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source", "checksum_sha256"),
                        name="company_dataset_source_checksum_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CompanyAlias",
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
                ("alias", models.CharField(max_length=255)),
                (
                    "normalized_alias",
                    models.CharField(db_index=True, editable=False, max_length=255),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aliases",
                        to="companies.company",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="company_aliases",
                        to="companies.companydatasource",
                    ),
                ),
            ],
            options={
                "ordering": ["alias"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "normalized_alias", "source"),
                        name="company_alias_source_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CompanySourceRecord",
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
                ("external_id", models.CharField(max_length=255)),
                ("source_record_url", models.URLField(blank=True, max_length=1500)),
                (
                    "confidence_score",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("raw_data", models.JSONField(default=dict)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="source_records",
                        to="companies.company",
                    ),
                ),
                (
                    "latest_dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="company_records",
                        to="companies.rawcompanydataset",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="company_records",
                        to="companies.companydatasource",
                    ),
                ),
            ],
            options={
                "ordering": ["company", "-confidence_score"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source", "external_id"),
                        name="company_source_external_id_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CompanyMetric",
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
                    "metric_name",
                    models.CharField(
                        choices=[
                            ("revenue", "Revenue"),
                            ("employee_count", "Employee count"),
                            ("customer_count", "Customer count"),
                            ("monthly_growth", "Monthly growth"),
                            ("burn_rate", "Burn rate"),
                            ("runway_months", "Runway (months)"),
                            ("funding_total", "Total funding"),
                            ("valuation", "Valuation"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "metric_value",
                    models.DecimalField(decimal_places=6, max_digits=24),
                ),
                ("metric_unit", models.CharField(max_length=30)),
                ("observation_date", models.DateField()),
                (
                    "confidence_score",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metrics",
                        to="companies.company",
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="metrics",
                        to="companies.rawcompanydataset",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="company_metrics",
                        to="companies.companydatasource",
                    ),
                ),
            ],
            options={
                "ordering": ["company", "-observation_date", "metric_name"],
                "indexes": [
                    models.Index(
                        fields=["metric_name", "-observation_date"],
                        name="company_metric_date_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "company",
                            "source",
                            "metric_name",
                            "observation_date",
                            "metric_unit",
                        ),
                        name="company_metric_observation_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CompanyOutcome",
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
                    "outcome_type",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("profitable", "Profitable"),
                            ("acquired", "Acquired"),
                            ("merged", "Merged"),
                            ("ipo", "IPO"),
                            ("pivoted", "Pivoted"),
                            ("closed", "Closed"),
                            ("inactive", "Inactive"),
                            ("unknown", "Unknown"),
                        ],
                        max_length=20,
                    ),
                ),
                ("outcome_date", models.DateField(blank=True, null=True)),
                ("reason", models.TextField(blank=True)),
                ("evidence_url", models.URLField(blank=True, max_length=1500)),
                (
                    "confidence_score",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outcomes",
                        to="companies.company",
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outcomes",
                        to="companies.rawcompanydataset",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="company_outcomes",
                        to="companies.companydatasource",
                    ),
                ),
            ],
            options={
                "ordering": ["company", "-outcome_date"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "source", "outcome_type", "outcome_date"),
                        name="company_outcome_evidence_unique",
                    )
                ],
            },
        ),
    ]
