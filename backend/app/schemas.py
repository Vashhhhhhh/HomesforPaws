"""
schemas.py — Pydantic Data Contracts (API Input/Output Shapes)
==============================================================
These classes define what data flows IN and OUT of the API.

Key Distinction from models.py:
  models.py  → Talks to the DATABASE (SQLAlchemy)
  schemas.py → Talks to the OUTSIDE WORLD (HTTP requests/responses)

Why keep them separate?
  1. Security: We can expose SOME fields to the API but keep others
     internal (e.g., never expose raw file paths to untrusted clients).
  2. Flexibility: The DB schema and the API shape can evolve independently.
  3. Validation: Pydantic validates incoming data BEFORE it touches the DB.

Naming Convention (Pattern to memorize):
  *Create  → What we ACCEPT when creating a resource (POST body)
  *Update  → What we ACCEPT when partially updating (PATCH body)
  *Response → What we RETURN to the client (GET response)
"""

from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional
from .models import VerificationStatus

# ============================================================
# USER SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    """
    What the client sends to CREATE a new user.
    We only accept name + email at signup.

    INTERN NOTE: We do NOT accept is_adopter_verified from the client.
    That field is controlled exclusively by the backend/admin system.
    If we let users set their own verification status, anyone could
    bypass the compliance checks. This is a classic broken access
    control vulnerability (OWASP Top 10 #1).
    """
    name: str
    email: EmailStr  # Pydantic validates this is a real email format


class UserResponse(BaseModel):
    """
    What the API RETURNS when a user is fetched.
    Notice: we expose the verification state — the client needs to
    know if they're verified. But we don't expose raw internal IDs
    in a way that could enable enumeration attacks (future concern).
    """
    id: int
    name: str
    email: EmailStr
    is_adopter_verified: VerificationStatus

    # This tells Pydantic to read from SQLAlchemy model attributes,
    # not just from dictionaries. Required for ORM integration.
    model_config = {"from_attributes": True}


class UserDocumentUpdate(BaseModel):
    """
    What the client sends to upload compliance document URLs.
    Both fields are Optional because they can upload one at a time.

    In production, these URLs would be pre-signed S3 URLs, not raw
    file paths. For Phase 1, we store the URL string as-is.
    """
    residency_proof_url: Optional[str] = None
    background_check_url: Optional[str] = None


# ============================================================
# PET SCHEMAS
# ============================================================

class PetCreate(BaseModel):
    """
    What the client sends to CREATE a new pet profile.

    CRITICAL: Notice what is NOT here:
      ✗ is_health_verified  — Set by the system, never by client input
      ✗ is_eligible_for_matching — Controlled by admin/Celery only
      ✗ owner_id — Will be injected from the authenticated user's session
                   (Phase 2, when we add JWT auth). For Phase 1, we
                   accept it in the body as a placeholder.

    vet_certificate_url and health_records_url are REQUIRED (not Optional)
    because per the blueprint, pets cannot exist without health documentation.
    """
    name: str
    description: Optional[str] = None
    owner_id: int  # TODO Phase 2: derive from JWT token, remove from body
    vet_certificate_toggle: bool
    health_records_toggle: bool
    has_picture_uploaded: bool



class PetResponse(BaseModel):
    """
    What the API RETURNS when a pet profile is fetched.
    We expose the fail-safe flags so the frontend can show
    verification status to the owner (e.g., "Pending Review" badge).
    """
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    vet_certificate_toggle: bool
    health_records_toggle: bool
    is_health_verified: bool
    is_eligible_for_matching: bool
    has_picture_uploaded: bool

    model_config = {"from_attributes": True}


# ============================================================
# UTILITY SCHEMAS
# ============================================================

class HealthCheckResponse(BaseModel):
    """Response for the root health-check endpoint."""
    status: str
    version: str
    message: str

class AdopterSurvey(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(...)
    housing_type: str = Field(..., examples=["Duplex", "Detached"])
    has_other_pets: bool = Field(default=False)
    lifestyle_description: str = Field(
        ...,
        min_length=150,
        max_length=1000,
        examples=["I live in a quiet suburban neighborhood with a large fenced yard. I work from home two days a week and am looking for a medium-sized dog that enjoys walks and playtime. I have previous experience owning dogs and am committed to providing a loving and stable environment."]
    )


class AdopterSurveyResponse(BaseModel):
    id: int
    name: str
    email: str
    housing_type: str
    has_other_pets: bool
    lifestyle_description: str

    model_config = {"from_attributes": True}


# ============================================================
# RECOMMENDATION SCHEMAS (Phase 1.3)
# ============================================================

class MatchRequest(BaseModel):
    """Input for the semantic matching endpoint."""
    survey_id: int


class MatchResult(BaseModel):
    """A single pet match result with its similarity score."""
    pet: PetResponse
    similarity_score: float  # 0.0 to 1.0, higher = better match