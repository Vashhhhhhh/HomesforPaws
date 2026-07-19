#  Homes4Paws: A Bidirectional Semantic Recommendation Engine

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![VectorDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-7015B2?style=flat)](https://github.com/chroma-core/chroma)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Asynchronous](https://img.shields.io/badge/Async%20Tasks-Celery%20%2B%20Redis-CC2027?style=flat&logo=redis&logoColor=white)](https://docs.celeryq.dev/)

PawsForward moves away from legacy, rigid keyword-filtered listing sites ("home_type = Detached Home") and replaces them with an intelligent, two-way matching engine.By converting unstructured lifestyle descriptions into high-dimensional vector embeddings, the system calculates semantic compatibility scores to maximize long-term animal placement success and reduce shelter overcrowding.

## Architecture
* **Semantic Matching Pipeline:** Leverages an LLM and ChromaDB vector database to evaluate unstructured adopter text against rich pet profiles using cosine similarity.
* **Hybrid Storage Architecture:** Combines PostgreSQL for ACID-compliant structured metadata (users, access control, identity) with a specialized vector database for semantic indexing.
* **Production-Grade Isolation:** Built with asynchronous task processing (Celery/Redis) for background check processing and clear Role-Based Access Control (RBAC) to enforce multi-tenant privacy.

**Asynchronous Compliance & Verification Engine:** Enforces business logic requiring mandatory verification gates (Veterinary Health Certifications, Proof of Residency, Criminal Background Checks) managed via a Celery/Redis task queue before enabling listing or matching states.
