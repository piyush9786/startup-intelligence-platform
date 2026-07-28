# Hybrid Research & Live Web Search RAG Architecture

## Overview

The `apps.research` module implements a hybrid RAG (Retrieval-Augmented Generation) pipeline combining internal verified database stores (PostgreSQL, Qdrant, Neo4j) with controlled live web search APIs (Tavily, Brave).

It powers real-time, evidence-grounded research reports for Indian startup founders using a private local LLM (`qwen3:4b` via Ollama).

---

## 1. System Dataflow

```text
Founder asks a question
          │
          ▼
React frontend
          │
          ▼
Django backend (apps.research)
          │
          ▼
Question and intent classifier (search_router.py)
          │
          ├── Historical/internal question
          │         │
          │         ▼
          │   PostgreSQL + Qdrant + Neo4j
          │
          └── Current/live-data question
                    │
                    ▼
              Web Search API (Tavily / Brave)
                    │
                    ▼
          Source validation & filtering (source_validator.py)
                    │
                    ▼
         Local knowledge + live evidence (evidence_ranker.py)
                    │
                    ▼
      Deterministic analytics & scoring (answer_context.py)
                    │
                    ▼
            Local Ollama LLM (qwen3:4b)
                    │
                    ▼
     Final answer with sources, dates,
      confidence and recommended actions
```

---

## 2. Component Breakdown

### 2.1 Intent Routing & Decision Engine (`services/search_router.py`)
Analyzes incoming founder queries for time-sensitive or dynamic market keywords (`latest`, `recent`, `currently`, `competitors`, `funding`, `deadlines`, `regulations`). If detected, `requires_live_search` is flagged `True` and live queries are scheduled.

### 2.2 Query Planning & Structured Idea Extraction (`services/query_planner.py`)
Transforms raw user text and startup profiles into structured JSON representations containing:
- Product category & sub-industry
- Target customer demographics
- Technology stack
- Regional geography & stage
- Revenue model

Generates targeted search query strings instead of sending raw user sentences directly to search APIs.

### 2.3 Search API Integrations (`services/tavily_client.py` & `services/brave_client.py`)
- Executes HTTP REST queries to Tavily API (`https://api.tavily.com/search`) or Brave Search API.
- All API keys are isolated in backend `.env` (`TAVILY_API_KEY`, `BRAVE_API_KEY`) and never exposed to client browsers or LLM prompts.

### 2.4 Source Validation & Authority Labeling (`services/source_validator.py`)
Classifies search result URLs into verification tiers:
- **`official_live`**: Government domains (`.gov.in`, `dpiit.gov.in`, `rbi.org.in`, `sebi.gov.in`).
- **`reputable_secondary`**: Verified tech and financial news (`inc42.com`, `yourstory.com`, `livemint.com`).
- **`unverified_live`**: General web sources.
- **`rejected`**: Invalid or broken URLs.

Computes SHA-256 content hashes to prevent duplicate evidence processing.

### 2.5 Evidence Extraction & Ranking (`services/evidence_extractor.py` & `services/evidence_ranker.py`)
Extracts text excerpts, assigns confidence scores ($0.0 - 1.0$), deduplicates content hashes, and ranks evidence by authority weighting.

### 2.6 Pre-Computed Analytics Engine (`services/answer_context.py`)
Computes financial and readiness metrics **prior to LLM invocation**:
- **Scenario Capital Forecasting**: Lean Prototype, Pilot & Certification, Commercial Launch.
- **Readiness Score**: Integer evaluation ($0 - 100$).
- **Competition & Market Concentration**: Statistically calculated parameters.

### 2.7 Ollama Report Generation (`services/report_generator.py`)
Invokes local `qwen3:4b` using Ollama's structured JSON schema feature. Generates structured output covering:
1. Startup Summary
2. Historical Peer Comparisons
3. Current Competitors
4. Recent Market Developments
5. Government Scheme Match
6. Risk Indicators
7. Market Gaps
8. Scenario Capital Requirements
9. Recommended Next Actions
10. Source Citations & Confidence

---

## 3. Database Schema

- **`ResearchRequest`**: Tracks job status (`queued`, `running`, `succeeded`, `failed`), intent classification, timing, and error logs.
- **`ResearchSearchQuery`**: Records executed search strings, provider name, and result counts.
- **`ResearchEvidence`**: Stores validated evidence excerpts, URLs, publishers, publication dates, hashes, confidence scores, and verification status.
- **`StartupResearchReport`**: Stores the final structured JSON report, model metadata, and source context snapshot.

---

## 4. REST API Endpoint Mapping

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/research/requests/` | Submit research question & launch Celery job |
| `GET` | `/api/v1/research/requests/<id>/` | Fetch job status, executed queries, and evidence items |
| `GET` | `/api/v1/research/reports/` | List all historical research reports for a profile |
| `GET` | `/api/v1/research/reports/<id>/` | View detailed structured research report |

---

## 5. Security & Safety Principles

1. **API Key Containment**: Search API keys are stored strictly in root `.env` and consumed by Django backend. Ollama and LLM models never receive or handle API keys.
2. **Scoped Access Control**: All endpoints enforce DRF `IsAuthenticated` policies. Non-staff users can only access research records associated with their owned `StartupProfile`.
3. **Deterministic Numerical Grounding**: Scenarios and score metrics are computed in Python. The LLM only explains and contextualizes pre-calculated values.
