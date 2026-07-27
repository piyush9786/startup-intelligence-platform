# Combined System Architecture & MCP Integration Blueprint

## Executive Summary

The Startup Intelligence Platform implements a dual-architecture paradigm:
1. **Online Serving Architecture**: Manages real-time founder idea submissions, profile normalization, multi-modal evidence retrieval, machine learning evaluations, and grounded LLM report generation.
2. **Offline Data Engineering Platform**: Continuously ingests, cleans, deduplicates, and enriches historical company data, government schemes, and market updates using scheduled pipelines and event streaming.

Together, the offline platform **builds intelligence** while the online architecture **delivers intelligence**. 

---

# 1. Recommended Combined System Architecture

```text
                                  USER
                                    │
           “I want to build a Smart Health Wristband Startup”
                                    │
                                    ▼
                         React + Vite Frontend
                    Idea Submission and Dashboard
                                    │
                                    ▼
                      Django REST Framework API
                                    │
                  Authentication + Authorization
                                    │
                                    ▼
                   Startup Intelligence Orchestrator
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
   Profile Extraction       Existing Startup Data     Live Research
   and Normalization         and Benchmarks            Gateway
           │                        │                        │
           │                        │                        │
      LLM extracts:          PostgreSQL                 Approved APIs
      • Industry             Neo4j                      Search providers
      • Business model       Qdrant                     Recent reports
      • Customer type        Gold datasets              News sources
      • Product category
      • Geography
      • Stage
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    ▼
                         Evidence Assembly Layer
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
   Structured Peer Search   Semantic Retrieval       Graph Retrieval
   SQL / ML similarity      Qdrant embeddings        Neo4j relations
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    ▼
                     Analytics and ML Intelligence
       ┌─────────────────────────────────────────────────────────┐
       │ • Comparable-company ranking                            │
       │ • Peer benchmark calculation                            │
       │ • Readiness assessment                                  │
       │ • Competition analysis                                  │
       │ • Risk indicators                                       │
       │ • Capital requirement scenarios                         │
       │ • Scheme eligibility                                    │
       │ • Funding-opportunity ranking                           │
       └─────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          Verified Evidence Package
                                    │
                                    ▼
                       Ollama LLM + RAG Generation
                                    │
                                    ▼
                      Personalized Startup Report
       ┌─────────────────────────────────────────────────────────┐
       │ • Comparable companies                                  │
       │ • Benchmark position                                    │
       │ • Market competition                                    │
       │ • Market gaps                                           │
       │ • Recommended differentiators                           │
       │ • Government schemes                                    │
       │ • Funding options                                       │
       │ • Capital scenarios                                     │
       │ • Risk indicators                                       │
       │ • Recommended next steps                                │
       │ • Sources and confidence                                │
       └─────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         React Dashboard Visualization
```

---

# 2. Offline Data Engineering Platform Layer

To prevent ad-hoc web searches during real-time user requests, canonical company intelligence and market data are processed continuously by an offline data platform:

```text
                    HISTORICAL AND LIVE DATA SOURCES
      Company datasets │ Government portals │ Reports │ APIs │ News
                                │
                                ▼
                         Apache Airflow
                 Scheduled ingestion and validation
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
            MinIO / S3                    Apache Kafka
          Raw data storage                Event streaming
          Bronze datasets                 Company events
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                           Apache Spark
              Clean, normalize, deduplicate and enrich
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
           PostgreSQL         Neo4j           Qdrant
           Structured         Company          Document
           analytics          relations        embeddings
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                    Startup Intelligence Backend
```

- **Apache Airflow**: Orchestrates batch ingestion, raw dataset registration, and periodic ETL pipelines.
- **Apache Kafka**: Handles real-time event streams (company updates, funding rounds, news triggers).
- **Apache Spark**: Executes batch and stream cleaning, entity resolution, deduplication, and feature vector extraction.
- **Derived Storage**:
  - **PostgreSQL**: Authoritative relational store for profiles, metrics, and application state.
  - **Qdrant**: Vector database for dense semantic embeddings.
  - **Neo4j**: Graph database for entity relationships (Company $\rightarrow$ Sector, Scheme $\rightarrow$ Prerequisite).

---

# 3. Model Context Protocol (MCP) Integration Layer

The **Model Context Protocol (MCP)** provides a standardized client-server protocol enabling Ollama and AI orchestrators to discover and invoke tools, inspect resources, and fill prompt templates.

## 3.1 Architecture & Placement

```text
                    Ollama / AI Orchestrator
                              │
                         MCP Client
                              │
       ┌──────────────────────┼────────────────────────┐
       │                      │                        │
       ▼                      ▼                        ▼
 Startup Data MCP       Analytics MCP           Research MCP
 Server                 Server                  Server
       │                      │                        │
       ▼                      ▼                        ▼
 PostgreSQL/Neo4j       Comparison APIs          Approved APIs
 Qdrant resources       Benchmark engine         Search gateway
```

## 3.2 Six Specialized MCP Servers

Instead of a single monolithic server, MCP capabilities are modularized by responsibility:

### 1. Startup Profile MCP Server
- **Tools**: `get_startup_profile`, `extract_startup_features`, `update_startup_profile`, `validate_startup_profile`
- **Resources**: `startup://profile/{startup_id}`, `startup://documents/{startup_id}`, `startup://requirements/{startup_id}`

### 2. Company Intelligence MCP Server
- **Tools**: `find_comparable_companies`, `get_company_details`, `get_company_metrics`, `get_company_outcomes`, `compare_company_timelines`
- **Resources**: `company://profile/{company_id}`, `company://metrics/{company_id}`, `company://evidence/{company_id}`

### 3. Benchmark MCP Server
- **Tools**: `get_industry_benchmark`, `get_stage_benchmark`, `calculate_percentile`, `calculate_peer_similarity`, `identify_risk_patterns`

### 4. Government Scheme MCP Server
- **Tools**: `search_schemes`, `check_scheme_eligibility`, `get_scheme_requirements`, `compare_scheme_options`
- **Resources**: `scheme://details/{scheme_id}`, `scheme://eligibility/{scheme_id}`, `scheme://evidence/{scheme_id}`

### 5. Research MCP Server
- **Tools**: `search_market_reports`, `search_recent_companies`, `search_competitor_updates`, `retrieve_source`
- **Constraints**: Accesses only approved allowlisted search gateways and API providers. Returns source URLs, retrieval timestamps, extracted facts, and confidence metrics.

### 6. Report Generation MCP Server
- **Tools**: `assemble_evidence_package`, `generate_report`, `validate_report_claims`, `store_report`

---

# 4. Strict Separation of Concerns

MCP is strictly an AI tool-integration interface. It does not replace core storage, pipelines, or application infrastructure:

```text
Kafka       → distributes events
Spark       → processes datasets
Airflow     → schedules pipelines
PostgreSQL  → stores structured records
Neo4j       → stores relationships
Qdrant      → retrieves semantically similar evidence
MCP         → exposes controlled data and tools to AI
Ollama      → reasons over evidence and explains results
Django      → enforces application rules and authorization
```

---

# 5. Key System Design Refinements

1. **Structured Profile Extraction**: LLM extraction targets a strictly typed JSON schema containing product category, industry, sub-industry, business model, target customer, technology stack, geography, stage, regulatory category, and revenue model rather than raw keyword strings.
2. **Dual-Path Similarity Engine**:
   - **Structured Company Similarity**: Evaluated via SQL/Spark feature distance (70% weight).
   - **Semantic Evidence Similarity**: Evaluated via Qdrant embeddings (30% weight).
3. **Pre-Computed Numerical Scoring**: Readiness scores, peer percentiles, eligibility matches, and capital requirements are calculated by deterministic Python/scikit-learn models before LLM invocation. The LLM's role is strictly explanation and contextualization.
4. **Scenario-Based Capital Requirements**: Capital projections present three scenarios (Lean Prototype, Pilot & Certification, Commercial Launch) with itemized cost assumptions.
5. **Controlled Live Search**: External queries pass through allowlist verification, claim extraction, confidence scoring, and temporary caching before reaching LLM context.
6. **Safe MCP Security**: Every MCP request is authenticated via Django REST Framework, scoped to authorized startup ownership (`user_id`, `startup_id`), and restricted by default-deny permission boundaries.

---

# 6. Final 8-Layer Architecture Overview

- **Layer 1: User Experience** — React + Vite (Glassmorphism, i18n, Interactive Dashboards)
- **Layer 2: Application API** — Django REST Framework (Default-Deny Authentication, Permissions, Rate Limits)
- **Layer 3: AI Orchestration** — Ollama, Prompt Management, MCP Client, Evidence Assembly, Response Validation
- **Layer 4: Intelligence Services** — Company Comparison, Benchmark Engine, Risk Engine, Scheme Matcher, Capital Forecasting, ML Models
- **Layer 5: Retrieval** — PostgreSQL Queries, Qdrant Vector Retrieval, Neo4j Graph Traversal, Approved Live Research
- **Layer 6: Data Engineering** — Airflow, Kafka, Spark, Data-Quality Validation
- **Layer 7: Storage** — PostgreSQL, MinIO / S3, Qdrant, Neo4j
- **Layer 8: Monitoring** — Prometheus, Grafana, Loki, Airflow & Kafka Monitoring
