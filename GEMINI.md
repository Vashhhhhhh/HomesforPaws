# PawsForward Project Configuration & Architecture Blueprint

## 🏛️ Project Identity & Scope
- **Name:** PawsForward
- **System Description:** Bidirectional Semantic Recommendation Engine for pet rehoming.
- **Goal:** Replace rigid keyword filters with vector embeddings to evaluate unstructured adopter text against rich pet profiles using cosine similarity.
- **Core Standard:** Maintain strict isolation, security states, and an asynchronous, state-driven document compliance pipeline.

---

## 🛠️ Tech Stack Constraints
- **Backend:** Python (FastAPI, Pydantic, SQLAlchemy ORM)
- **Primary Database:** PostgreSQL (Tracks system state, configurations, and relational metadata)
- **Vector Database:** ChromaDB (Handles vector listings and high-dimensional semantic indexing)
- **Asynchronous Stack:** Celery + Redis (Handles processing background tasks and document analysis pipelines)
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (Fetch API asynchronous requests, zero framework overhead)

---

## 🗄️ Database & State-Machine Engineering

### 1. Compliance Verification Enums
All document verification gates must adhere to this lifecycle state structure:
- `PENDING`: Uploaded, awaiting verification check.
- `APPROVED`: Passed criteria; system unlock.
- `REJECTED`: Failed verification criteria; access denied.

### 2. Core Object Data Schemas
- **User (Adopters/Owners):**
  - Columns: `id` (PK), `name`, `email` (Unique).
  - Adopter Compliance: `residency_proof_url` (String, nullable), `background_check_url` (String, nullable).
  - Validation State: `is_adopter_verified` (Enum: PENDING/APPROVED/REJECTED).
- **Pet Profiles:**
  - Columns: `id` (PK), `owner_id` (FK -> users.id), `name`.
  - Rehoming Compliance: `vet_certificate_url` (String, required), `health_records_url` (String, required).
  - Validation State: `is_health_verified` (Enum: PENDING/APPROVED/REJECTED).
  - Engine Guard Flag: `is_eligible_for_matching` (Boolean, default=False).

### ⚠️ Critical Architecture Constraints (Fail-Safe Flags)
- **Rule 1:** A pet profile CANNOT be injected or indexed into ChromaDB vector space unless `is_health_verified` is toggled to `APPROVED`.
- **Rule 2:** The matching engine must enforce a circuit-breaker check where `is_eligible_for_matching` must be explicitly `True` before any adopter query can match against that animal.
- **Rule 3 (RBAC Multi-Tenancy Privacy):** Surrendering owners must never be able to view private contact details of an adopting user until a match has been programmatically and mutually accepted via the backend interface.

---

## 📁 Required Directory Layout
Enforce the following workspace separation of concerns structure:
```text
pawsforward/
├── GEMINI.md            <-- This context rule configuration
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py      # Entry point & CORS routing gateway
│   │   ├── schemas.py   # Pydantic data modeling & API guards
│   │   └── models.py    # SQLAlchemy permanent core schemas
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js