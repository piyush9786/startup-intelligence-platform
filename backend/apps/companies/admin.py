from django.contrib import admin

from .models import (
    Company,
    CompanyAlias,
    CompanyDataSource,
    CompanyMetric,
    CompanyOutcome,
    CompanySourceRecord,
    RawCompanyDataset,
)


class CompanyAliasInline(admin.TabularInline):
    model = CompanyAlias
    extra = 0


class CompanySourceRecordInline(admin.TabularInline):
    model = CompanySourceRecord
    extra = 0
    readonly_fields = ("raw_data",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "canonical_name",
        "industry",
        "business_model",
        "country",
        "operating_status",
        "verification_status",
    )
    list_filter = (
        "industry",
        "business_model",
        "country",
        "operating_status",
        "verification_status",
    )
    search_fields = ("canonical_name", "normalized_name", "website", "aliases__alias")
    readonly_fields = ("normalized_name", "created_at", "updated_at")
    inlines = (CompanyAliasInline, CompanySourceRecordInline)


@admin.register(CompanyDataSource)
class CompanyDataSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "reliability_score",
        "verification_status",
        "active",
        "last_retrieved_at",
    )
    list_filter = ("source_type", "verification_status", "active")
    search_fields = ("name", "slug", "publisher")


@admin.register(RawCompanyDataset)
class RawCompanyDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset_id",
        "source",
        "parsing_status",
        "row_count",
        "accepted_count",
        "rejected_count",
        "retrieved_at",
    )
    list_filter = ("parsing_status", "source", "schema_version")
    search_fields = ("dataset_id", "original_filename", "checksum_sha256")
    readonly_fields = (
        "checksum_sha256",
        "content_length",
        "row_count",
        "accepted_count",
        "rejected_count",
        "error_message",
        "metadata",
        "created_at",
        "updated_at",
    )


@admin.register(CompanyMetric)
class CompanyMetricAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "metric_name",
        "metric_value",
        "metric_unit",
        "observation_date",
        "confidence_score",
        "source",
    )
    list_filter = ("metric_name", "metric_unit", "source")
    search_fields = ("company__canonical_name",)


@admin.register(CompanyOutcome)
class CompanyOutcomeAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "outcome_type",
        "outcome_date",
        "confidence_score",
        "source",
    )
    list_filter = ("outcome_type", "source")
    search_fields = ("company__canonical_name", "reason")
