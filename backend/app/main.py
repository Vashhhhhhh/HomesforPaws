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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from .models import Base
from .schemas import HealthCheckResponse


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
    print("🚀 PawsForward API starting up...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified/created.")
    yield  # ← Server is live and handling requests here
    print("🛑 PawsForward API shutting down.")


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
