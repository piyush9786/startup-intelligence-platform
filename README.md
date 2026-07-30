# Startup Intelligence Platform

> **Laptop quick start:** run `./bootstrap_current_project.sh` from the project
> root, or `./bootstrap_current_project.sh --gpu` for NVIDIA Ollama acceleration.
> See [`LAPTOP_SETUP.md`](docs/setup/LAPTOP_SETUP.md) for prerequisites, diagnostics,
> catalog recovery, and all service addresses.

A verified startup-support intelligence platform for readiness assessment,
scheme eligibility, recommendations, evidence verification, grounded guidance,
deterministic dependency-aware funding planning, and **integrated multi-model AI/ML data engineering**.

The platform combines a verified deterministic data core with a **9-model ML ensemble** and an enhanced **3-stage RAG pipeline**.

The historical-company foundation adds governed raw-dataset registration,
source provenance, canonical company identities, append-only metric
observations, outcome evidence, and idempotent CSV ingestion. See
[`docs/data-foundation-v1.md`](docs/data-foundation-v1.md) and
[`docs/architecture/COMBINED_ARCHITECTURE_V2.md`](docs/architecture/COMBINED_ARCHITECTURE_V2.md) for full architectural blueprints.

---

## Core Principles

1. **Deterministic Engines Decide**: Core eligibility, funding amounts, deadlines, and prerequisite graph rules are enforced deterministically.
2. **ML Models Predict & Rank**: Learning models handle feature extraction, startup cohort clustering, scheme success probability ranking, anomaly detection, and capital forecasting.
3. **Generative AI Explains**: Language models retrieve, summarize, and explain recommendations with grounded citations — without inventing facts.

---

## Founder Operations Workflows

The authenticated API now includes founder-owned operational workflows rather
than read-only discovery alone:

- `GET|POST /api/v1/compliance-records/` — compliance registrations, issue and
  expiry dates, renewal reminders, status and summary counts.
- `GET|POST /api/v1/founder-vault-documents/` — private MinIO-backed founder
  document vault with owner-scoped listing and authenticated downloads.
- `GET|POST /api/v1/consultant-profiles/` — consultant marketplace profiles,
  expertise, languages, state coverage, availability and verification state.
- `GET|POST /api/v1/application-tasks/` — due-dated tasks attached to the
  existing scheme application tracker.
- `GET /api/v1/application-stage-events/` — immutable application-stage audit
  history.
- `POST /api/v1/application-workflows/{id}/transition/` — validated transitions
  through draft, submitted, under-review, approved and rejected stages.

Every founder-owned queryset is scoped to the authenticated account. A founder
cannot list, download, update or transition another founder's records.

---

## 🤖 Integrated 9 ML Models Architecture

The platform embeds **9 specialized ML models** across 4 functional layers:

| # | Model | Algorithm | Engine / Library | Purpose |
|---|-------|-----------|------------------|---------|
| **1** | **Transformer Embeddings** | `embeddinggemma` | Ollama | **RAG Vector Search** — encodes scheme PDFs & queries into Qdrant dense vectors |
| **2** | **Generative AI / LLM** | `qwen3:4b` | Ollama | **Reasoning & Chat** — site-wide copilot, document parsing, scheme summaries |
| **3** | **K-Means Clustering** | `KMeans(n_clusters=8)` | `scikit-learn` | **Startup Cohort Segmentation** — groups startups into cohorts by stage, sector, & turnover |
| **4** | **SVM Classifier** | `CalibratedClassifierCV(SVC)` | `scikit-learn` | **Scheme Success Ranking** — predicts probability (0.0–1.0) of a startup successfully acquiring a scheme |
| **5** | **AdaBoost Classifier** | `AdaBoostClassifier` | `scikit-learn` | **Readiness Predictor** — predicts probability of a startup becoming "READY" within 30 days |
| **6** | **Isolation Forest** | `IsolationForest` | `scikit-learn` | **Anomaly & Fraud Detection** — flags statistically anomalous or fraudulent startup profiles |
| **7** | **TF-IDF + Cosine** | `TfidfVectorizer` | `scikit-learn` | **Hybrid RAG Retrieval** — sparse keyword search combined with Qdrant via Reciprocal Rank Fusion (RRF) |
| **8** | **Random Forest Regressor** | `RandomForestRegressor` | `scikit-learn` | **Capital Runway Forecasting** — sector-aware ML runway estimation for the AI Capital Planner |
| **9** | **DBSCAN Clustering** | `DBSCAN` | `scikit-learn` | **Scheme Deduplication** — clusters embedding vectors to flag near-duplicate government scheme versions |

---

## 🔄 Enhanced 3-Stage RAG Pipeline

```text
Stage 1: HYBRID RETRIEVAL
  User Query ─┬─► Embedding (embeddinggemma) ─► Dense Search (Qdrant)  ─┐
             └─► Sparse TF-IDF (Model 7)     ─► Keyword Search        ─┴─► Reciprocal Rank Fusion (RRF) [Top 20]

Stage 2: ML RE-RANKING
  Top 20 Candidates ─► Calibrated SVM Ranker (Model 4) ─► Success Probability Ranking [Top 6]

Stage 3: LLM GROUNDED EXPLANATION
  Top 6 Chunks + Startup Profile ─► LLM (qwen3:4b) ─► Grounded Answer + Source Citations
```

---

## 🏗️ Data Engineering & MLOps Infrastructure

- **29-Dimensional Feature Store (`MLFeatureStore`)**: Pandas/NumPy feature engineering pipeline extracting stage ordinals, log-scaled financial metrics (turnover, team size, funding required), DPIIT/Udyam status, readiness scores, and 18-sector one-hot encodings.
- **Model Registry (`MLModelRegistry`)**: Tracks every trained model artifact (`.joblib`), version number, training dataset size, primary metrics (silhouette score, accuracy, MAE, ROC-AUC), and active state.
- **Celery Beat Batch Pipelines**:
  - `nightly_feature_extraction`: 24-hour periodic ETL caching feature vectors for all startup profiles.
  - `nightly_anomaly_and_cohort`: Automated nightly Isolation Forest anomaly scanning & K-Means re-clustering.
  - `weekly_model_retraining`: Automatic weekly re-training of all scikit-learn model artifacts.
- **Bootstrap Synthetic Data Generator**: Provides realistic training distributions for initial zero-data deployments.

---

## 🏛️ System Architecture

```text
React 19 / Vite (React Router v7, TanStack Query v5, i18n context)
      │
      ▼ (HTTP / REST API — Default-Deny IsAuthenticated Permission Policy)
Django 5.2 + Django REST Framework 3.16 (modular app-level `urls.py` routing)
      │
      ├── PostgreSQL — Authoritative business data, MLFeatureStore & MLModelRegistry
      ├── Redis / Celery — Asynchronous tasks & scheduled ML retraining
      ├── scikit-learn / joblib — ML Engine (K-Means, SVM, AdaBoost, Isolation Forest, RF, TF-IDF, DBSCAN)
      ├── Qdrant — Vector database for dense RAG embeddings
      ├── Neo4j — Verified dependency graph projection
      ├── MinIO — Raw document storage & private evidence uploads
      └── Ollama — Local LLM (qwen3:4b) & Embeddings (embeddinggemma)
```

---

## 📁 Project Structure

```text
startup-intelligence-platform/
├── .env / .env.example       # Local development environment configuration
├── .env.production.example  # Production environment manifest template
├── .gitignore                # Ignore rules (excludes staticfiles, ml_models, node_modules)
├── docker-compose.yml        # Local orchestration (Backend, Postgres, Redis, Qdrant, Neo4j, MinIO, Ollama)
├── docker-compose.prod.yml   # Production orchestration (Gunicorn, Nginx, Postgres, Redis, Celery, Qdrant)
├── Makefile                  # Developer workflow shortcuts
├── README.md                 # Primary project overview
├── backend/                  # Django REST Framework Backend
│   ├── apps/
│   │   ├── accounts/         # Auth & JWT management (urls.py)
│   │   ├── assistant/        # Chatbot & AI sessions (urls.py)
│   │   ├── core/             # Shared base models & health views (urls.py)
│   │   ├── discovery/        # Web crawler & URL frontier (urls.py)
│   │   ├── documents/        # Document extraction & chunking (urls.py)
│   │   ├── knowledge/        # RAG embeddings & vector search (urls.py)
│   │   ├── ml_engine/        # 9-Model ML Engine, Feature Store, Shadow Mode, & Celery Tasks
│   │   ├── recommendations/  # Eligibility engine & SVM scheme ranking (urls.py)
│   │   ├── schemes/          # Scheme catalog & dependency graph (urls.py)
│   │   ├── sources/          # Data source registry (urls.py)
│   │   └── startups/         # Profiles, operations, readiness, vault, consultant marketplace, and capital planning
│   ├── catalog/              # Data source discovery catalog
│   ├── config/               # Django config, Celery, & modular settings/ package
│   │   ├── settings/         # Base, Development, & Production settings (base.py, development.py, production.py)
│   │   └── urls.py           # Clean root URL routing featuring modular app includes
│   ├── ml_models/            # Trained .joblib model artifacts (gitignored)
│   ├── scripts/              # Startup scripts (`start-web.sh`)
│   ├── manage.py             # Django CLI
│   ├── pyproject.toml        # Ruff linter config
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React 19 + Vite Frontend
│   ├── src/                  # React components, AppShell router, DashboardHome, i18n, API clients, & styles
│   │   ├── AppShell.jsx      # URL-based route container with route adapters (React Router v7)
│   │   ├── DashboardHome.jsx # Standalone decoupled Founder Command Center dashboard view
│   │   ├── main.jsx          # Root entry wrapping AppShell in BrowserRouter & QueryClientProvider
│   │   ├── responsive.css    # Mobile-first founder workspace overrides
│   │   └── components/ui.jsx # Shared UI primitives
│   ├── package.json          # Frontend dependencies (react-router-dom, @tanstack/react-query)
│   └── vite.config.js        # Vite configuration (outDir: "dist")
├── docs/                     # Architecture, setup, operations and domain documentation
│   ├── setup/                # Laptop setup and end-to-end startup guides
│   └── changes/              # Historical implementation change notes
└── infrastructure/           # Deployment scripts
```

---

## 🚀 Local Setup & Production Deployment

### 1. Local Development
```bash
chmod +x bootstrap_current_project.sh scripts/*.sh
./bootstrap_current_project.sh
```

For NVIDIA GPU acceleration:

```bash
./bootstrap_current_project.sh --gpu
```

The laptop bootstrap creates safe local environment values, starts every
service, applies migrations, creates MinIO buckets, imports the verified scheme
catalog and external support datasets, and runs `platform_doctor --strict`.
See [`LAPTOP_SETUP.md`](docs/setup/LAPTOP_SETUP.md) for administration, diagnostics,
reset, live-search, and troubleshooting commands.

To import the sample historical-company dataset after startup:

```bash
docker compose exec backend python manage.py import_companies \
  --file /data/samples/indian_b2b_saas_demo.csv \
  --source-slug example-company-source \
  --source-name "Example company source" \
  --reliability-score 0.800
```

### 2. Production Deployment
```bash
# 1. Configure production environment variables
cp .env.production.example .env.production

# 2. Build deployable images
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  build

# 3. Run the mandatory one-time release phase
#    This applies migrations, imports bundled catalogs, and collects static files.
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  --profile release \
  run --rm release

# 4. Start Gunicorn, Nginx, workers, databases, and supporting services
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  up -d

# 5. Perform production security check
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  exec backend python manage.py check --deploy
```

Production startup rejects missing, short, or placeholder values for
`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, and
`MINIO_SECRET_KEY`. `DJANGO_ALLOWED_HOSTS` and `MINIO_ACCESS_KEY` must also be
set explicitly.

### ML Management Command Usage
```bash
# Train all models with synthetic data (bootstrap mode)
docker compose exec backend python manage.py train_ml_models --synthetic

# Train all models with real database data (requires ≥50 profiles; skips unlabelled supervised models safely in batch runs)
docker compose exec backend python manage.py train_ml_models --real

# Train a specific model
docker compose exec backend python manage.py train_ml_models --model svm
docker compose exec backend python manage.py train_ml_models --model kmeans
```

---

## 🌐 Local URLs

- **Web App**: <http://localhost:5173>
- **API Health**: <http://localhost:8000/api/v1/health/>
- **API Swagger Docs**: <http://localhost:8000/api/docs/>
- **Django Admin**: <http://localhost:8000/admin/> (includes ML Model Registry & Feature Store views)
- **Qdrant Dashboard**: <http://localhost:6333/dashboard>
- **Neo4j Browser**: <http://localhost:7474>
- **MinIO Console**: <http://localhost:9001>
- **Mailpit**: <http://localhost:8025>

---

## 🧪 Validation & Testing

```bash
# Backend pytest suite, ruff linting, migration drift, & deployment check
docker compose exec -T backend pytest -q
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py makemigrations --check --dry-run
docker compose exec -T backend python manage.py check --deploy --settings=config.settings.production

# Frontend test suite, linting & production build validation
docker compose exec -T frontend npm test
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run build
```
