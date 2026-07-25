"""
Feature Engineering Pipeline (Data Engineering Layer)

Extracts, transforms, and normalizes raw StartupProfile fields into a
fixed-length numeric feature vector ready for scikit-learn model input.

Feature vector layout (28 dimensions):
  [0]     stage_encoded (ordinal 0–7)
  [1]     startup_age_days (log-scaled, 0–1)
  [2]     team_size (log-scaled, 0–1)
  [3]     annual_turnover (log-scaled, 0–1)
  [4]     funding_required (log-scaled, 0–1)
  [5]     dpiit_recognized (0/1)
  [6]     udyam_registered (0/1)
  [7]     readiness_score (0–1)
  [8]     recommendation_count (0–1 normalized, capped at 20)
  [9]     founder_gender_male (0/1)
  [10]    founder_gender_female (0/1)
  [11-28] sector one-hot (top 18 sectors)
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np

from apps.startups.models import StartupProfile

FEATURE_VERSION = "features-v1"
FEATURE_DIM = 29  # 11 base features + 18 sector one-hot slots (indices 11-28)

_STAGE_ORDER = {
    StartupProfile.Stage.IDEA: 0,
    StartupProfile.Stage.VALIDATION: 1,
    StartupProfile.Stage.PROTOTYPE: 2,
    StartupProfile.Stage.MVP: 3,
    StartupProfile.Stage.PILOT: 4,
    StartupProfile.Stage.EARLY_REVENUE: 5,
    StartupProfile.Stage.GROWTH: 6,
    StartupProfile.Stage.EXPANSION: 7,
}

_TOP_SECTORS = [
    "agritech", "edtech", "fintech", "healthtech", "cleantech",
    "ecommerce", "logistics", "manufacturing", "iot", "saas",
    "deeptech", "biotech", "foodtech", "retail", "hrtech",
    "legaltech", "proptech", "traveltech",
]


def _log_scale(value: float | None, max_value: float) -> float:
    """Log-scale and normalize a value to [0, 1]."""
    if not value or value <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(max_value))


def _latest_readiness_score(startup: StartupProfile) -> float:
    """Return the most recent readiness score as 0–1, or 0 if none."""
    assessment = startup.readiness_assessments.order_by("-created_at").first()
    if assessment is None:
        return 0.0
    return assessment.score / 100.0


def _recommendation_count(startup: StartupProfile) -> float:
    """Return normalized recommendation count (capped at 20)."""
    count = startup.recommendations.count()
    return min(1.0, count / 20.0)


def extract_features(startup: StartupProfile) -> np.ndarray:
    """
    Extract a 28-dimensional feature vector from a StartupProfile.

    Returns a float64 numpy array of shape (28,).
    """
    vec = np.zeros(FEATURE_DIM, dtype=np.float64)

    # [0] Stage ordinal
    stage_idx = _STAGE_ORDER.get(startup.stage, 0)
    vec[0] = stage_idx / 7.0  # normalize to 0–1

    # [1] Startup age in days (log-scaled, max 10 years)
    if startup.incorporation_date:
        age_days = (date.today() - startup.incorporation_date).days
        vec[1] = _log_scale(age_days, 3650)

    # [2] Team size (log-scaled, max 500)
    vec[2] = _log_scale(float(startup.team_size or 0), 500)

    # [3] Annual turnover (log-scaled, max 1 crore)
    vec[3] = _log_scale(float(startup.annual_turnover or 0), 10_000_000)

    # [4] Funding required (log-scaled, max 10 crore)
    vec[4] = _log_scale(float(startup.funding_required or 0), 100_000_000)

    # [5] DPIIT recognized
    vec[5] = 1.0 if startup.dpiit_recognized else 0.0

    # [6] Udyam registered
    vec[6] = 1.0 if startup.udyam_registered else 0.0

    # [7] Latest readiness score
    vec[7] = _latest_readiness_score(startup)

    # [8] Normalized recommendation count
    vec[8] = _recommendation_count(startup)

    # [9–10] Founder gender
    gender = (startup.founder_gender or "").lower()
    vec[9] = 1.0 if gender == "male" else 0.0
    vec[10] = 1.0 if gender == "female" else 0.0

    # [11–28] Sector one-hot
    sectors_lower = [s.lower() for s in (startup.sectors or [])]
    for i, sector in enumerate(_TOP_SECTORS):
        if sector in sectors_lower:
            vec[11 + i] = 1.0

    return vec


def batch_extract_features(startups: Any) -> tuple[np.ndarray, list[int]]:
    """
    Batch extract feature vectors for a queryset of StartupProfiles.

    Returns:
        X: np.ndarray of shape (n_samples, FEATURE_DIM)
        ids: list of startup primary keys aligned with X rows
    """
    X_list: list[np.ndarray] = []
    ids: list[int] = []

    for startup in startups.prefetch_related("readiness_assessments", "recommendations"):
        X_list.append(extract_features(startup))
        ids.append(startup.pk)

    if not X_list:
        return np.empty((0, FEATURE_DIM), dtype=np.float64), []

    return np.vstack(X_list), ids
