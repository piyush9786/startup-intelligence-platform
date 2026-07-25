"""
Scheme Deadline & Regulatory Renewal Notification Service.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.startups.models import StartupProfile

logger = logging.getLogger(__name__)


def generate_founder_notification_alerts(profile: StartupProfile) -> list[dict[str, Any]]:
    """
    Generates actionable notification alerts for scheme deadlines, GST renewals,
    and profile verification gates.
    """
    alerts: list[dict[str, Any]] = []

    # 1. GSTIN Check
    if not profile.gstin:
        alerts.append({
            "id": "alert-gstin-missing",
            "tone": "amber",
            "title": "GSTIN Registration Unverified",
            "message": (
                "Enter your 15-digit GSTIN to unlock GST tax "
                "exemption schemes and instant verification."
            ),
            "action_view": "startup",
            "action_label": "Enter GSTIN",
        })

    # 2. DPIIT Check
    if not profile.dpiit_recognized:
        alerts.append({
            "id": "alert-dpiit-missing",
            "tone": "info",
            "title": "DPIIT Recognition Available",
            "message": (
                "Apply for DPIIT Recognition to claim 3-year income tax "
                "exemptions & Startup India Seed Fund."
            ),
            "action_view": "schemes",
            "action_label": "Explore DPIIT Schemes",
        })

    # 3. Readiness Blocker Alert
    if profile.readiness_score and profile.readiness_score < 70:
        alerts.append({
            "id": "alert-readiness-low",
            "tone": "red",
            "title": "Readiness Score Below Scheme Thresholds",
            "message": (
                f"Current readiness is {profile.readiness_score}/100. "
                "Resolve critical blockers to qualify for high-ticket grants."
            ),
            "action_view": "roadmap",
            "action_label": "Fix Readiness Blockers",
        })

    # 4. Anomaly Warning
    if profile.is_anomalous:
        alerts.append({
            "id": "alert-anomaly-review",
            "tone": "red",
            "title": "Profile Verification Review Pending",
            "message": (
                "Your profile has been flagged for statistical "
                "verification by the ML engine. Update details to resolve."
            ),
            "action_view": "startup",
            "action_label": "Review Profile",
        })

    return alerts
