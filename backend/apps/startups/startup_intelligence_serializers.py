"""
Serializers for the Founder Intelligence Dashboard aggregate snapshot.
All fields are read-only; the view builds the payload and validates it here.
"""

from __future__ import annotations

from rest_framework import serializers


class ReadinessSnapshotSerializer(serializers.Serializer):
    score = serializers.IntegerField(allow_null=True)
    grade = serializers.CharField(allow_null=True, allow_blank=True)
    domain_count = serializers.IntegerField()
    critical_gap_count = serializers.IntegerField()
    has_assessment = serializers.BooleanField()


class CapitalSnapshotSerializer(serializers.Serializer):
    runway_months = serializers.FloatField(allow_null=True)
    runway_status = serializers.CharField(allow_null=True, allow_blank=True)
    net_burn = serializers.FloatField(allow_null=True)
    has_plan = serializers.BooleanField()


class MilestonesSnapshotSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    blocked = serializers.IntegerField()
    completion_pct = serializers.IntegerField()


class BuilderSnapshotSerializer(serializers.Serializer):
    sections_confirmed = serializers.IntegerField()
    sections_drafted = serializers.IntegerField()
    sections_total = serializers.IntegerField()
    completion_pct = serializers.IntegerField()


class SchemesSnapshotSerializer(serializers.Serializer):
    matched = serializers.IntegerField()
    eligible = serializers.IntegerField()
    conditionally_eligible = serializers.IntegerField()
    pending_review = serializers.IntegerField()
    has_recommendations = serializers.BooleanField()


class RecentActivityItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    label = serializers.CharField()
    workspace = serializers.CharField()
    occurred_at = serializers.CharField(allow_null=True)


class FounderIntelligenceSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField()
    startup_name = serializers.CharField()
    generated_at = serializers.CharField()
    readiness = ReadinessSnapshotSerializer()
    capital = CapitalSnapshotSerializer()
    milestones = MilestonesSnapshotSerializer()
    builder = BuilderSnapshotSerializer()
    schemes = SchemesSnapshotSerializer()
    recent_activity = RecentActivityItemSerializer(many=True)
    weakest_workspace = serializers.CharField()
