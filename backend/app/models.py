"""
models.py — SQLAlchemy ORM Models (Permanent Database Schema)
=============================================================
These classes map 1:1 to database TABLES.
When the app starts, SQLAlchemy uses these to create/validate the schema.

Architecture Notes:
- models.py only talks to the DATABASE.
- It does NOT know about HTTP, JSON, or the API layer.
- The Pydantic schemas in schemas.py handle the API contract.
"""

from sqlalchemy import Boolean
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship, DeclarativeBase


# ============================================================
# DATABASE BASE CLASS
# ============================================================
# All SQLAlchemy models must inherit from a common Base.
# This Base is how SQLAlchemy knows which classes represent tables.
class Base(DeclarativeBase):
    pass


# ============================================================
# STATE MACHINE: Verification Status Enum
# ============================================================
# This enum enforces the compliance lifecycle defined in GEMINI.md.
#
# INTERN NOTE: Why an Enum and not a plain string column?
#   → Strings are unbounded. "approved", "Approved", "APPROVED" are
#     three different values. An Enum makes the database enforce the
#     contract. Only PENDING, APPROVED, or REJECTED can exist.
#
# LIFECYCLE:
#   PENDING → APPROVED  (passes verification)
#   PENDING → REJECTED  (fails verification)
#   REJECTED → PENDING  (re-submission — handled in Phase 3 via Celery)
# ============================================================
class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ============================================================
# USER MODEL
# ============================================================
# Represents BOTH adopters AND surrendering owners.
# Role differentiation will be added in Phase 2 (RBAC).
#
# Compliance Columns (from GEMINI.md §Rule 3):
#   - residency_proof_url: nullable — they may not have uploaded yet
#   - background_check_url: nullable — same reason
#   - is_adopter_verified: defaults PENDING — always starts unverified
#
# INTERN NOTE: nullable=True is an explicit choice, not laziness.
#   It means "this data is optional at creation time but required
#   before the system will allow matching." The verification state
#   tracks whether it's been provided AND approved.
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)

    # --- Compliance Documents ---
    residency_proof_url = Column(String, nullable=True)
    background_check_url = Column(String, nullable=True)

    # --- Verification State Machine ---
    # CRITICAL: Defaults to PENDING. Must be explicitly APPROVED by
    # an admin or async Celery task before adopter can match pets.
    is_adopter_verified = Column(
        SAEnum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
        server_default=VerificationStatus.PENDING.value,
    )

    # --- Relationship ---
    # One user can list MANY pets. SQLAlchemy handles the JOIN for us.
    # back_populates="owner" links this to Pet.owner below.
    pets = relationship("Pet", back_populates="owner")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} verified={self.is_adopter_verified}>"


# ============================================================
# PET MODEL
# ============================================================
# Represents a pet profile submitted for rehoming.
#
# FAIL-SAFE FLAGS (from GEMINI.md — Non-Negotiable):
#
#   RULE 1: is_health_verified must be APPROVED before ChromaDB
#           indexing is ever triggered.
#
#   RULE 2: is_eligible_for_matching must be explicitly True before
#           ANY adopter query can match against this animal.
#           Default = False. NEVER opt-in by accident.
#
# The separation of these two flags is intentional:
#   - is_health_verified = "are the documents valid?"
#   - is_eligible_for_matching = "is the system ALLOWED to surface this pet?"
#
# This gives admins a manual override. Even if health docs pass,
# an admin can hold is_eligible_for_matching=False for any reason.
# ============================================================
class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # --- Foreign Key (Relational Integrity) ---
    # If the owner (User) is deleted, what happens to their pets?
    # We'll handle cascade rules in Phase 2. For now, restrict deletion.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # --- Pet Description (used for vector embedding in Phase 3+) ---
    # Text is used (not String) because descriptions can be long.
    # String maps to VARCHAR; Text maps to TEXT — no length limit.
    description = Column(Text, nullable=True)

    # --- Compliance Documents (REQUIRED, not nullable) ---
    # Per GEMINI.md: both are required for health verification.
    vet_certificate_toggle = Column(Boolean, nullable=True)
    health_records_toggle = Column(Boolean, nullable=True)
    has_picture_uploaded = Column(Boolean, nullable=False, default=False)

    # --- FAIL-SAFE FLAG #1: Health Document Verification State ---
    # Controls whether docs have been reviewed and approved.
    is_health_verified = Column(
        Boolean,
        nullable=False,
        default=False
    )

    # --- FAIL-SAFE FLAG #2: Matching Engine Circuit Breaker ---
    # This is the GATE to ChromaDB. This boolean MUST be True
    # before the pet profile can be indexed or surfaced in queries.
    # It is set to False by default. Intentional. Explicit. Safe.
    is_eligible_for_matching = Column(Boolean, nullable=False, default=False)

    # --- Relationship (back-reference to owner) ---
    owner = relationship("User", back_populates="pets")

    def __repr__(self) -> str:
        return (
            f"<Pet id={self.id} name={self.name} "
            f"health={self.is_health_verified} "
            f"eligible={self.is_eligible_for_matching}>"
        )


# ============================================================
# ADOPTER SURVEY MODEL
# ============================================================
# Stores the adopter intake survey submitted via the frontend form.
#
# No foreign key to users yet — adopters are anonymous in Phase 1.
# In Phase 2, when JWT auth is added, this will link to users.id
# so we can associate a survey with a verified adopter account.
# ============================================================
class AdopterSurvey(Base):
    __tablename__ = "adopter_surveys"

    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String, nullable=False)
    email                 = Column(String, nullable=False, index=True)
    housing_type          = Column(String, nullable=False)
    has_other_pets        = Column(Boolean, nullable=False, default=False)
    lifestyle_description = Column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<AdopterSurvey id={self.id} email={self.email}>"
