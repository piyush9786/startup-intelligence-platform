"""
Synthetic Data Generator for ML Model Training

Generates realistic training datasets for all 7 scikit-learn models
when no real historical data is available (initial deployment).

Data is generated to mimic the real distribution of Indian startup profiles
including stages, sectors, DPIIT status, and funding patterns.
"""
from __future__ import annotations

import random

import numpy as np

from apps.ml_engine.services.feature_pipeline import FEATURE_DIM

_RNG = np.random.default_rng(seed=42)
_STAGES = [0.0, 1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7, 1.0]
_SECTORS = list(range(18))  # 18 one-hot sector slots


def _random_startup_vector() -> np.ndarray:
    """Generate a single synthetic startup feature vector (28-dim)."""
    vec = np.zeros(FEATURE_DIM, dtype=np.float64)
    vec[0] = random.choice(_STAGES)
    vec[1] = _RNG.uniform(0, 1)   # age
    vec[2] = _RNG.uniform(0, 0.5)  # team size (smaller startups)
    vec[3] = _RNG.uniform(0, 0.4)  # turnover
    vec[4] = _RNG.uniform(0, 0.6)  # funding required
    vec[5] = _RNG.choice([0.0, 1.0], p=[0.4, 0.6])  # DPIIT
    vec[6] = _RNG.choice([0.0, 1.0], p=[0.5, 0.5])  # Udyam
    vec[7] = _RNG.uniform(0.3, 1.0)  # readiness score (realistic range)
    vec[8] = _RNG.uniform(0, 0.5)    # recommendation count
    gender = _RNG.choice([0, 1, 2], p=[0.55, 0.40, 0.05])
    vec[9] = 1.0 if gender == 0 else 0.0
    vec[10] = 1.0 if gender == 1 else 0.0
    # Assign 1-3 random sectors
    for s in _RNG.choice(_SECTORS, size=_RNG.integers(1, 4), replace=False):
        vec[11 + s] = 1.0
    return vec


def generate_startup_features(n: int = 500) -> np.ndarray:
    """Generate n synthetic startup feature vectors."""
    return np.vstack([_random_startup_vector() for _ in range(n)])


def generate_svm_dataset(
    n: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate (X, y) for SVM training.
    X: startup (28) + scheme (4) features = 32 dims
    y: binary label — 1=scheme likely to succeed, 0=not
    """
    X_list, y_list = [], []
    for _ in range(n):
        startup_vec = _random_startup_vector()
        # Scheme features: [min_amt, max_amt, equity, is_open]
        scheme_vec = np.array(
            [
                _RNG.uniform(0, 0.5),
                _RNG.uniform(0.5, 2.0),
                float(_RNG.integers(0, 2)),
                float(_RNG.integers(0, 2)),
            ],
            dtype=np.float64,
        )
        combined = np.concatenate([startup_vec, scheme_vec])

        # Label heuristic: DPIIT + high readiness + open scheme → likely success
        dpiit = startup_vec[5]
        readiness = startup_vec[7]
        is_open = scheme_vec[3]
        prob_success = 0.3 + 0.3 * dpiit + 0.2 * readiness + 0.2 * is_open
        label = int(_RNG.random() < prob_success)

        X_list.append(combined)
        y_list.append(label)

    return np.vstack(X_list), np.array(y_list)


def generate_adaboost_dataset(n: int = 500) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate (X, y) for AdaBoost training.
    y: 1 = startup will become READY in 30 days, 0 = will not
    """
    X = generate_startup_features(n)
    # Startups with high readiness + small teams → more likely to close gaps quickly
    readiness = X[:, 7]
    team_small = (X[:, 2] < 0.3).astype(float)
    prob_ready = 0.2 + 0.5 * readiness + 0.1 * team_small + 0.1 * X[:, 5]
    y = (_RNG.random(n) < prob_ready).astype(int)
    return X, y


def generate_capital_dataset(n: int = 500) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate (X, y) for Random Forest capital runway prediction.
    X: startup (28) + capital (4) features = 32 dims
    y: runway months (float)
    """
    X_list, y_list = [], []
    for _ in range(n):
        sv = _random_startup_vector()
        cap = _RNG.uniform(0.05, 5.0)    # available capital (normalized)
        rev = _RNG.uniform(0, 1.0)       # monthly revenue
        fixed = _RNG.uniform(0.1, 0.8)
        var = _RNG.uniform(0.05, 0.3)
        capital_vec = np.array([cap, rev, fixed, var], dtype=np.float64)

        net_burn = max(0.001, (fixed + var) - rev)
        runway = min(99.0, cap / net_burn)
        # Add sector noise: tech sectors typically burn faster
        runway *= _RNG.uniform(0.8, 1.2)

        X_list.append(np.concatenate([sv, capital_vec]))
        y_list.append(float(runway))

    return np.vstack(X_list), np.array(y_list)
