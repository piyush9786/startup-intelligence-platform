# Architecture

## Architectural style

The Startup Intelligence Platform is a modular Django monolith with a React
frontend, asynchronous Celery workers, and a **dedicated 9-model Machine Learning & Data Engineering engine**.

The modular monolith keeps transactions, permissions, and audit trails simple
while preserving service boundaries that may later be extracted if scale
requires it.

## Core Architecture Documents

- **[Combined System Architecture & MCP Integration Blueprint](COMBINED_ARCHITECTURE_V2.md)**
- **[Hybrid Research & Live Web Search RAG Architecture](HYBRID_RESEARCH_RAG_ARCHITECTURE.md)**
- **[9-Model Machine Learning Engine & Data Engineering Pipeline](ML_ENGINE_V1.md)**
- **[Modular App Routing, Settings Package & Default-Deny Security](MODULAR_ROUTING_AND_SECURITY_V1.md)**
- **[Verified Scheme Prerequisite Graph](SCHEME_PREREQUISITE_GRAPH_V1.md)**
- **[Shared Agent Orchestration Persistence](SHARED_AGENT_ORCHESTRATION_V1.md)**
- **[Site-Wide Founder Chatbot](SITE_WIDE_CHATBOT_V1.md)**

## System overview

```text
Founder / Reviewer / Administrator
                │
                ▼
          React + Vite (with i18n)
                │
                ▼
      Django REST Framework
                │
   ┌────────────┼────────────────┬────────────────┐
   ▼            ▼                ▼                ▼
PostgreSQL   Celery/Redis   scikit-learn     Derived stores
(Auth, DB,   (Async & ML    (ML Models:      (Qdrant, Neo4j,
 FeatureStore) Retraining)   SVM, KMeans, RF)  MinIO, Ollama)
```

## Source of truth

PostgreSQL is authoritative for:

- users and permissions;
- sources and source documents;
- canonical schemes and scheme versions;
- verified executable rules;
- startup profiles and assessment drafts;
- readiness assessments and action plans;
- eligibility assessments;
- recommendation runs and snapshots;
- verification submissions, evidence metadata, and immutable decisions;
- advisor jobs and briefing snapshots;
- **`MLFeatureStore` pre-computed feature vectors and cohort assignments**;
- **`MLModelRegistry` trained model artifact versions and performance metrics**.

MinIO stores raw object bytes.
PostgreSQL stores their metadata and access relationships.
Qdrant and Neo4j are derived vector and graph projections.

---

## 🤖 Integrated 9-Model ML Engine & Data Engineering (`apps.ml_engine`)

The platform integrates **9 Machine Learning models** to upgrade every decision boundary from static heuristics to data-driven learning:

### 1. Data Engineering Pipeline
- **`MLFeatureStore`**: Computes a 29-dimensional normalized feature vector for every `StartupProfile` (stage ordinal, log-scaled turnover/team size/funding, DPIIT/Udyam status, readiness score, and 18-sector one-hot encoding).
- **`MLModelRegistry`**: Version control for trained `.joblib` model binaries, tracking training sample sizes, accuracy, silhouette scores, MAE, and ROC-AUC metrics.
- **Celery Beat Pipelines**: Nightly feature ETL, nightly Isolation Forest anomaly scanning, and weekly automatic model retraining.

### 2. The 9-Model Ensemble

| # | Model | Algorithm | Engine | Function |
|---|-------|-----------|--------|----------|
| **1** | Transformer Embeddings | `embeddinggemma` | Ollama | Encodes scheme text chunks into 768-dim vectors in Qdrant |
| **2** | Generative AI / LLM | `qwen3:4b` | Ollama | Site-wide chatbot, document auto-fill, grounded briefings |
| **3** | K-Means Clustering | `KMeans(n_clusters=8)` | `scikit-learn` | Groups startups into cohorts by stage, sector, and turnover |
| **4** | SVM Classifier | `CalibratedClassifierCV(SVC)` | `scikit-learn` | Predicts probability (0.0–1.0) of scheme acquisition success |
| **5** | AdaBoost Classifier | `AdaBoostClassifier` | `scikit-learn` | Predicts probability of startup becoming READY in 30 days |
| **6** | Isolation Forest | `IsolationForest` | `scikit-learn` | Detects statistically anomalous or fraudulent startup profiles |
| **7** | TF-IDF + RRF | `TfidfVectorizer` | `scikit-learn` | Sparse keyword retrieval merged with Qdrant via Reciprocal Rank Fusion |
| **8** | Random Forest | `RandomForestRegressor` | `scikit-learn` | ML-adjusted capital runway prediction for AI Capital Planner |
| **9** | DBSCAN | `DBSCAN` | `scikit-learn` | Identifies near-duplicate scheme versions using vector distance |

### 3. Enhanced 3-Stage RAG Pipeline
1. **Hybrid Retrieval**: Parallel search across Qdrant (dense vectors) + TF-IDF (sparse keywords), merged using Reciprocal Rank Fusion ($K=60$).
2. **ML Re-Ranking**: Top candidates re-ranked by Calibrated SVM success probability ($0.40 \times \text{eligibility} + 0.40 \times \text{SVM} + 0.10 \times \text{rules} + 0.10 \times \text{status}$).
3. **LLM Explanation**: Top 6 candidates passed to `qwen3:4b` with strict citation bounds.

---

## Domain boundaries

### Frontend
Built on React + Vite: i18n localization (English, Hindi, Marathi), modern glassmorphism UI/UX, responsive routing, AI Capital Planner UI, site-wide copilot drawer.

### Schemes
Canonical programmes, immutable `SchemeVersion` records, eligibility requirements, and executable rules.

### Recommendations
Combines executable rules with the **SVM Scheme Ranker (Model 4)** to compute multi-factor recommendation scores and persist immutable recommendation runs.

### Startups
Owns startup profiles, assessment drafts, readiness plans, capital plans (integrated with **Random Forest Model 8**), and advisor snapshots.

### ML Engine (`apps.ml_engine`)
Owns feature engineering, model registry, model persistence (`.joblib`), batch training tasks, synthetic data generation, and inference endpoints for all 7 scikit-learn models.

### Research (`apps.research`)
Owns live web search RAG integration, query planning, intent classification, source authority validation, content hash deduplication, pre-computed analytics assembly, and grounded Ollama report generation.
