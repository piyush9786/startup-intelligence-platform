# System Architecture

## Architecture Overview

Startup Intelligence Platform follows a modular full-stack architecture.

```text
                        +----------------------+
                        |       User           |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        |   React Frontend     |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        |    Django Backend    |
                        |      REST APIs       |
                        +----------+-----------+
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
+------------------+    +------------------+    +------------------+
| Startup Services |    | Research Engine  |    | AI Assistant     |
+------------------+    +------------------+    +------------------+
                                 |
                                 v
                       +---------------------+
                       | Query Planning      |
                       | Research Intent     |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       | Live Search Router  |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       | Source Validation   |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       | Evidence Extraction |
                       | Evidence Ranking    |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       | Report Generation   |
                       | Decision Engine     |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       | Intelligence Memory |
                       +---------------------+

          +------------------+     +------------------+
          | PostgreSQL       |     | Redis            |
          +------------------+     +------------------+

          +------------------+     +------------------+
          | Qdrant / Vector  |     | MinIO            |
          | Knowledge Store  |     | Object Storage   |
          +------------------+     +------------------+
Research Architecture

The research engine is designed to prevent the final report from relying only on raw LLM generation.

Instead, the system follows an evidence-first workflow:
Question
   |
   v
Research Intent
   |
   v
Query Planner
   |
   v
Multiple Search Queries
   |
   v
Live Search
   |
   v
Source Validation
   |
   v
Evidence Extraction
   |
   v
Evidence Scoring
   |
   v
Ranking and Deduplication
   |
   v
Grounded Report Generation
   |
   v
Decision Intelligence
Data Storage
PostgreSQL

Stores application data including:

Startup information
Research requests
Search queries
Research evidence
Generated reports
Intelligence memory
Strategic decisions
Redis

Supports background processing and application caching.

Vector Database

Supports semantic retrieval for knowledge and RAG workflows.

Object Storage

MinIO is used for application storage requirements where object storage is needed.

Deployment

The application is containerized using Docker and Docker Compose.

The architecture allows backend services, frontend services, databases, caching, search infrastructure, and AI services to run as separate containers.
