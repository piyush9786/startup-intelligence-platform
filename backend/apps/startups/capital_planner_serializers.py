"""
Serializers for the AI Capital Planner endpoints.
"""
from rest_framework import serializers

from .models import StartupCapitalPlan


class StartupCapitalPlanSerializer(serializers.ModelSerializer):
    runway_status_display = serializers.CharField(
        source="get_runway_status_display",
        read_only=True,
    )

    class Meta:
        model = StartupCapitalPlan
        fields = (
            "id",
            "available_capital",
            "monthly_revenue",
            "fixed_costs",
            "variable_costs",
            "net_burn",
            "runway_months",
            "runway_status",
            "runway_status_display",
            "scenarios",
            "allocations",
            "sensitivity",
            "ai_explanation",
            "plan_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StartupCapitalPlanGenerateSerializer(serializers.Serializer):
    available_capital = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0
    )
    monthly_revenue = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, default=0
    )
    fixed_costs = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0
    )
    variable_costs = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0
    )
