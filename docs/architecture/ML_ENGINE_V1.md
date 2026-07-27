# 9-Model Machine Learning Engine & Data Engineering Pipeline (`v1`)

## Overview

The `apps.ml_engine` Django application provides a multi-model machine learning architecture and automated data engineering pipeline for the Startup Intelligence Platform.

Rather than relying purely on static heuristics or unconstrained generative AI, the platform combines **deterministic rules** (which decide eligibility) with **9 specialized ML models** (which segment, predict, rank, detect anomalies, and forecast metrics).

---

## 🤖 The 9 ML Models Ensemble

| # | Model | Algorithm / Implementation | Library | Function & Domain |
|---|-------|----------------------------|---------|-------------------|
| **1** | **Transformer Embeddings** | `embeddinggemma` | Ollama | **RAG Vector Search** — encodes scheme text & user queries into 768-dim Qdrant vectors. |
| **2** | **Generative AI / LLM** | `qwen3:4b` | Ollama | **Reasoning & Chat** — site-wide copilot, document autofill, grounded advisor briefings. |
| **3** | **K-Means Clustering** | `KMeans(n_clusters=8)` | `scikit-learn` | **Startup Cohort Segmentation** — groups startups by stage, sector, turnover, and team size. |
| **4** | **Calibrated SVM** | `CalibratedClassifierCV(SVC)` | `scikit-learn` | **Scheme Success Ranking** — predicts probability ($0.0-1.0$) of a startup acquiring a scheme. |
| **5** | **AdaBoost Classifier** | `AdaBoostClassifier` | `scikit-learn` | **Readiness Predictor** — predicts probability of a startup achieving `READY` status in 30 days. |
| **6** | **Isolation Forest** | `IsolationForest` | `scikit-learn` | **Anomaly & Fraud Detection** — flags statistically anomalous or spam startup profiles. |
| **7** | **TF-IDF + Cosine** | `TfidfVectorizer` | `scikit-learn` | **Hybrid Search Index** — sparse keyword retrieval merged with Qdrant via Reciprocal Rank Fusion ($K=60$). |
| **8** | **Random Forest Regressor** | `RandomForestRegressor` | `scikit-learn` | **Capital Runway Forecasting** — sector-aware ML runway estimation for AI Capital Planner. |
| **9** | **DBSCAN** | `DBSCAN(eps=0.08)` | `scikit-learn` | **Scheme Deduplication** — clusters embedding vectors to flag duplicate scheme versions. |

---

## 🏗️ Data Engineering Layer & Feature Store

### 29-Dimensional Feature Store (`MLFeatureStore`)
The feature extraction pipeline (`apps.ml_engine.services.feature_pipeline`) extracts a 29-dimensional normalized feature vector from `StartupProfile`:

- `[0]`: Stage ordinal ($0.0-1.0$)
- `[1]`: Startup age in days (log-scaled, max 10 years)
- `[2]`: Team size (log-scaled, max 500)
- `[3]`: Annual turnover (log-scaled, max ₹1 crore)
- `[4]`: Funding required (log-scaled, max ₹10 crore)
- `[5]`: DPIIT recognition binary ($0/1$)
- `[6]`: Udyam registration binary ($0/1$)
- `[7]`: Latest readiness score ($0.0-1.0$)
- `[8]`: Recommendation count ($0.0-1.0$)
- `[9-10]`: Founder gender one-hot (Male/Female)
- `[11-28]`: Sector one-hot encoding (18 top sector slots)

### Model Registry (`MLModelRegistry`)
Database model tracking trained `.joblib` model artifact versions:
- Stores `model_type`, `model_version`, `status` (`active`, `retired`), `training_sample_count`, `primary_metric_name`, and `primary_metric_value`.
- Keeps serialized binaries in `backend/ml_models/` directory.

---

## 🔄 Celery Batch Jobs (`apps.ml_engine.tasks`)

1. **`nightly_feature_extraction`**: Nightly 24-hour periodic task extracting & updating `MLFeatureStore` feature vectors.
2. **`nightly_anomaly_and_cohort`**: Nightly job running Isolation Forest anomaly scoring + K-Means cohort re-clustering across all profiles.
3. **`weekly_model_retraining`**: Weekly scheduled re-training job (`python manage.py train_ml_models`) to update active `.joblib` model binaries.
4. **`on_demand_scheme_dedup`**: DBSCAN deduplication over Qdrant embedding vectors.

---

## 🔄 3-Stage Hybrid RAG Pipeline

```text
Stage 1: HYBRID RETRIEVAL
  User Query ─┬─► Embedding (embeddinggemma) ─► Qdrant Dense Search ─┐
             └─► Sparse TF-IDF (Model 7)     ─► Keyword Search     ─┴─► Reciprocal Rank Fusion (RRF) [Top 20]

Stage 2: ML RE-RANKING
  Top 20 Candidates ─► Calibrated SVM Ranker (Model 4) ─► Success Probability Ranking [Top 6]

Stage 3: LLM GROUNDED EXPLANATION
  Top 6 Chunks + Startup Profile ─► LLM (qwen3:4b) ─► Grounded Answer + Source Citations
```

---

## 🛠️ Management Command & CLI Usage

```bash
# Train all models with synthetic data (bootstrap mode)
python manage.py train_ml_models --synthetic --samples 800

# Train all models with real database data
python manage.py train_ml_models --real

# Train specific model only
python manage.py train_ml_models --model svm
python manage.py train_ml_models --model kmeans
```
