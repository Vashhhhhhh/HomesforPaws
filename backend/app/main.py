"""
main.py — FastAPI Application Entry Point & CORS Gateway
=========================================================
This is where the server starts. Every HTTP request to your backend
enters through this file first.

Responsibility of this file:
  1. Create the FastAPI app instance
  2. Mount middleware (CORS — so the browser can call our API)
  3. Connect to the database and create tables on startup
  4. Register route handlers (or include routers from other modules)

What this file does NOT do:
  - Business logic (that lives in route handlers / services)
  - Data modeling (that's models.py)
  - Schema validation (that's schemas.py)

INTERN NOTE: Notice the lifespan context manager below.
  FastAPI replaced the old @app.on_event("startup") pattern.
  The lifespan function runs setup code on start and teardown on stop.
  This is the modern, recommended way to handle app lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from .models import Base, AdopterSurvey as AdopterSurveyModel, Pet as PetModel
from .schemas import (
    HealthCheckResponse, AdopterSurvey, AdopterSurveyResponse,
    PetCreate, PetResponse, MatchRequest, MatchResult,
)
from . import vector_store



# ============================================================
# DATABASE SETUP
# ============================================================
# Import database URL from environment (loaded from .env file).
# NEVER hardcode credentials in source code. This is a cardinal rule.
#
# For now we use a sync engine. In Phase 3, we'll switch to
# asyncpg + SQLAlchemy async for full non-blocking I/O.
import os
from dotenv import load_dotenv

load_dotenv()  # Reads .env file and injects values into os.environ

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pawsforward_dev.db")
# ↑ Fallback to SQLite for local dev if no .env is set.
# This lets you run the app instantly without a Postgres instance.
# Production MUST use PostgreSQL. The .env file controls this.

engine = create_engine(DATABASE_URL, echo=True)
# echo=True logs every SQL statement — useful for learning/debugging.
# Set to False in production.

# Database session factory.
# Each request gets its own session, which is closed after the request completes.
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency: yields a DB session per request, then closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# APPLICATION LIFESPAN
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs BEFORE the server starts accepting requests (startup phase).
    `create_all` inspects all models imported from models.py and creates
    any tables that don't yet exist in the database.

    INTERN NOTE: In production, we will use Alembic migrations instead
    of create_all. Why? create_all can't handle schema CHANGES — it only
    creates tables that are missing. Alembic tracks every schema change
    as a versioned migration file, like git for your database schema.
    """
    print("[START] PawsForward API starting up...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables verified/created.")
    yield  # ← Server is live and handling requests here
    print("[STOP] PawsForward API shutting down.")


# ============================================================
# FASTAPI APP INSTANCE
# ============================================================
app = FastAPI(
    title="PawsForward API",
    description=(
        "Bidirectional Semantic Recommendation Engine for pet rehoming. "
        "Replaces keyword filters with vector embeddings to match adopters "
        "with pets using cosine similarity scoring."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # Docs will be available at /docs (Swagger UI)
    # Redoc alternative at /redoc
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================
# Cross-Origin Resource Sharing (CORS):
# Browsers block JavaScript from calling APIs on a different domain/port
# by default. This middleware tells the browser "yes, this frontend
# is allowed to talk to this backend."
#
# During development, we allow all origins ("*").
# In production, replace with your exact frontend domain.
#
# INTERN NOTE: Never ship allow_origins=["*"] to production.
# It lets ANY website on the internet call your API as an authenticated
# user. Instead, specify: allow_origins=["https://pawsforward.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to production domain in deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES — Phase 1 Skeleton
# ============================================================

@app.get("/", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint. Used by load balancers, monitoring tools,
    and you — to confirm the API is alive.

    This is the FIRST thing you should hit when you boot the server.
    If this returns 200, the server is running.
    """
    return HealthCheckResponse(
        status="ok",
        version="0.1.0",
        message="PawsForward API is operational. Welcome to Phase 1.",
    )


# ============================================================
# PHASE 2 PLACEHOLDERS
# ============================================================
# These routers will be uncommented and implemented in Phase 2
# when we add actual CRUD endpoints for Users and Pets.
#
# from .routers import users, pets
# app.include_router(users.router, prefix="/users", tags=["Users"])
# app.include_router(pets.router, prefix="/pets", tags=["Pets"])

@app.get("/health")
def get_health():
  return {"status": "ok", "message": "PawsForward API is online and accepting connections."}


@app.post("/api/v1/surveys/adopter", response_model=AdopterSurveyResponse, tags=["Surveys"])
def submit_adopter_survey(survey: AdopterSurvey, db: Session = Depends(get_db)):
    """
    Accept and persist an adopter intake survey.
    Validates the payload via Pydantic, writes it to the adopter_surveys table,
    and returns the stored record including its generated database ID.
    """
    record = AdopterSurveyModel(**survey.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/surveys/adopter", response_model=List[AdopterSurveyResponse], tags=["Surveys"])
def list_adopter_surveys(db: Session = Depends(get_db)):
    """Return all submitted adopter surveys."""
    return db.query(AdopterSurveyModel).all()


@app.get("/api/v1/pets", response_model=List[PetResponse], tags=["Pets"])
def get_pet_profiles(db: Session = Depends(get_db)):
    """Return all pet profiles from the database."""
    return db.query(PetModel).all()


@app.post("/api/v1/pets", response_model=PetResponse, tags=["Pets"])
def create_pet_profile(pet: PetCreate, db: Session = Depends(get_db)):
    """
    Create and persist a new pet profile.
    Validates payload via Pydantic, persists to database, returns created record.
    """
    record = PetModel(
        name=pet.name,
        description=pet.description,
        owner_id=pet.owner_id,
        vet_certificate_toggle=pet.vet_certificate_toggle,
        health_records_toggle=pet.health_records_toggle,
        has_picture_uploaded=pet.has_picture_uploaded,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ============================================================
# PHASE 1.3 — Semantic Matching Engine
# ============================================================

@app.post("/api/v1/pets/{pet_id}/activate", response_model=PetResponse, tags=["Pets"])
def activate_pet(pet_id: int, db: Session = Depends(get_db)):
    """
    Dev-only endpoint: marks a pet as health-verified and eligible for matching,
    then indexes its description into ChromaDB for semantic search.

    In production, this would be triggered by the compliance pipeline
    after document verification passes.
    """
    pet = db.query(PetModel).filter(PetModel.id == pet_id).first()
    if not pet:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Pet with id {pet_id} not found.")

    if not pet.description:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Pet has no description. Cannot index into vector DB.")

    # Set compliance flags.
    pet.is_health_verified = True
    pet.is_eligible_for_matching = True
    db.commit()
    db.refresh(pet)

    # Index into ChromaDB.
    vector_store.index_pet(pet.id, pet.description)

    return pet


@app.post("/api/v1/pets/{pet_id}/deactivate", response_model=PetResponse, tags=["Pets"])
def deactivate_pet(pet_id: int, db: Session = Depends(get_db)):
    """
    Remove a pet from the matching engine.
    Sets is_eligible_for_matching=False and removes its vector from ChromaDB.
    """
    pet = db.query(PetModel).filter(PetModel.id == pet_id).first()
    if not pet:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Pet with id {pet_id} not found.")

    pet.is_eligible_for_matching = False
    db.commit()
    db.refresh(pet)

    # Remove from ChromaDB.
    vector_store.remove_pet(pet.id)

    return pet


@app.post("/api/v1/recommendations/match", response_model=List[MatchResult], tags=["Recommendations"])
def match_adopter_to_pets(request: MatchRequest, db: Session = Depends(get_db)):
    """
    Semantic matching endpoint.
    Takes an adopter survey ID, encodes the lifestyle description into a vector,
    and queries ChromaDB for the most similar pet profiles.
    Returns ranked results with similarity scores.
    """
    # 1. Fetch the adopter survey.
    survey = db.query(AdopterSurveyModel).filter(AdopterSurveyModel.id == request.survey_id).first()
    if not survey:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Survey with id {request.survey_id} not found.")

    # 2. Query ChromaDB for similar pet vectors.
    raw_matches = vector_store.query_matches(survey.lifestyle_description, top_k=5)

    if not raw_matches:
        return []

    # 3. Fetch full pet records from SQLite for the matched IDs.
    pet_ids = [m["pet_id"] for m in raw_matches]
    pets = db.query(PetModel).filter(PetModel.id.in_(pet_ids)).all()
    pet_lookup = {p.id: p for p in pets}

    # 4. Build response, preserving ChromaDB ranking order.
    results = []
    for match in raw_matches:
        pet = pet_lookup.get(match["pet_id"])
        if pet and pet.is_eligible_for_matching:
            results.append(MatchResult(
                pet=PetResponse.model_validate(pet),
                similarity_score=match["similarity_score"],
            ))

    return results
