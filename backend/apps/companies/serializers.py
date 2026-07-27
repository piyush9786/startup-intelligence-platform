from rest_framework import serializers

from .models import (
    Company,
    CompanyAlias,
    CompanyDataSource,
    CompanyMetric,
    CompanyOutcome,
    RawCompanyDataset,
)


class CompanyAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyAlias
        fields = ("alias",)


class CompanyMetricSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = CompanyMetric
        fields = (
            "id",
            "metric_name",
            "metric_value",
            "metric_unit",
            "observation_date",
            "confidence_score",
            "source_name",
        )


class CompanyOutcomeSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = CompanyOutcome
        fields = (
            "id",
            "outcome_type",
            "outcome_date",
            "reason",
            "evidence_url",
            "confidence_score",
            "source_name",
        )


class CompanyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "canonical_name",
            "industry",
            "sub_industry",
            "business_model",
            "customer_segment",
            "country",
            "state",
            "city",
            "founded_year",
            "website",
            "operating_status",
            "verification_status",
        )


class CompanyDetailSerializer(CompanyListSerializer):
    aliases = CompanyAliasSerializer(many=True, read_only=True)
    metrics = CompanyMetricSerializer(many=True, read_only=True)
    outcomes = CompanyOutcomeSerializer(many=True, read_only=True)
    provenance_count = serializers.IntegerField(read_only=True)

    class Meta(CompanyListSerializer.Meta):
        fields = CompanyListSerializer.Meta.fields + (
            "aliases",
            "metrics",
            "outcomes",
            "provenance_count",
            "created_at",
            "updated_at",
        )


class CompanyDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDataSource
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class RawCompanyDatasetSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = RawCompanyDataset
        fields = "__all__"
        read_only_fields = tuple(field.name for field in RawCompanyDataset._meta.fields)
