# Generated for Adviser Decision Intelligence v1.
# ADVISER_DECISION_INTELLIGENCE_V1
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("research", "0006_research_first_workflow")]

    operations = [
        migrations.CreateModel(
            name="ResearchInsight",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("insight_type", models.CharField(choices=[("benefit", "Benefit"), ("competitor", "Competitor"), ("success_case", "Success case"), ("failure_case", "Failure case"), ("challenge", "Challenge"), ("opportunity", "Opportunity"), ("risk", "Risk"), ("market_gap", "Market gap"), ("lesson", "Lesson")], max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("summary", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("evidence_urls", models.JSONField(blank=True, default=list)),
                ("confidence_score", models.FloatField(default=0.5)),
                ("freshness_status", models.CharField(choices=[("current", "Current"), ("aging", "Aging"), ("stale", "Stale"), ("reverify", "Reverify")], default="current", max_length=16)),
                ("last_verified_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("source_report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="structured_insights", to="research.startupresearchreport")),
                ("startup_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="research_insights", to="startups.startupprofile")),
            ],
            options={"ordering": ["-last_verified_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="DecisionRecommendation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("question", models.TextField()),
                ("recommended_direction", models.TextField()),
                ("rationale", models.TextField(blank=True, default="")),
                ("alternatives", models.JSONField(blank=True, default=list)),
                ("decision_matrix", models.JSONField(blank=True, default=list)),
                ("conditions_to_reconsider", models.JSONField(blank=True, default=list)),
                ("immediate_actions", models.JSONField(blank=True, default=list)),
                ("action_plan", models.JSONField(blank=True, default=dict)),
                ("confidence_score", models.FloatField(default=0.5)),
                ("generated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("source_report", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="decision_recommendation", to="research.startupresearchreport")),
                ("startup_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decision_recommendations", to="startups.startupprofile")),
            ],
            options={"ordering": ["-generated_at", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="researchinsight",
            index=models.Index(fields=["startup_profile", "insight_type", "last_verified_at"], name="research_insight_profile_idx"),
        ),
        migrations.AddConstraint(
            model_name="researchinsight",
            constraint=models.UniqueConstraint(fields=("source_report", "insight_type", "title"), name="research_unique_report_insight"),
        ),
        migrations.AddConstraint(
            model_name="researchinsight",
            constraint=models.CheckConstraint(condition=models.Q(confidence_score__gte=0.0, confidence_score__lte=1.0), name="research_insight_conf_rng"),
        ),
        migrations.AddIndex(
            model_name="decisionrecommendation",
            index=models.Index(fields=["startup_profile", "generated_at"], name="research_decision_profile_idx"),
        ),
        migrations.AddConstraint(
            model_name="decisionrecommendation",
            constraint=models.CheckConstraint(condition=models.Q(confidence_score__gte=0.0, confidence_score__lte=1.0), name="research_decision_conf_rng"),
        ),
    ]
