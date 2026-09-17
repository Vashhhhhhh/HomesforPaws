"""
vector_store.py — ChromaDB + SentenceTransformers Service
==========================================================
Owns all vector embedding and similarity search logic.

bridge between the relational world (SQLite/PostgreSQL)
and the vector world (ChromaDB). It handles:
  1. Converting text descriptions into 384-dimensional vector embeddings
  2. Storing those vectors in a persistent ChromaDB collection
  3. Querying for the nearest vectors given a text query

Architecture:
  - main.py calls functions from this module
  - This module does NOT know about FastAPI, HTTP, or Pydantic
  - It only talks to ChromaDB and the SentenceTransformers model

The transformer model (all-MiniLM-L6-v2) is loaded lazily on first use
to avoid blocking the server on every --reload cycle during development.
"""

import os
from pathlib import Path

# Force HuggingFace model cache into the project directory.
# This keeps the ~90MB model download contained and easy to delete.
_HF_CACHE_DIR = str(Path(__file__).resolve().parent.parent / ".hf_cache")
os.environ["HF_HOME"] = _HF_CACHE_DIR

import chromadb

# ============================================================
# SINGLETON STATE
# ============================================================
# These are module-level singletons. They get initialized once
# on first use and reused for the lifetime of the process.

_model = None          # SentenceTransformer model instance
_chroma_client = None  # ChromaDB persistent client
_collection = None     # ChromaDB collection for pet profiles


def _get_model():
    """
    Lazy-load the SentenceTransformer model on first call.
    Subsequent calls return the cached instance.

    Why lazy? The model takes ~2-5 seconds to load. If we loaded it
    at import time, every uvicorn --reload cycle would block for that
    duration. Lazy loading means it only loads when actually needed.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("[VECTOR] Loading SentenceTransformer model (first time only)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[VECTOR] Model loaded successfully.")
    return _model


def _get_collection():
    """
    Get or create the ChromaDB collection for pet profiles.
    Uses PersistentClient so vectors survive server restarts.
    """
    global _chroma_client, _collection
    if _collection is None:
        chroma_data_dir = str(Path(__file__).resolve().parent.parent / "chroma_data")
        print(f"[VECTOR] Initializing ChromaDB at: {chroma_data_dir}")
        _chroma_client = chromadb.PersistentClient(path=chroma_data_dir)
        _collection = _chroma_client.get_or_create_collection(
            name="pet_profiles",
            metadata={"description": "Pet profile description embeddings for semantic matching"},
        )
        print(f"[VECTOR] ChromaDB collection 'pet_profiles' ready. Current count: {_collection.count()}")
    return _collection


# ============================================================
# PUBLIC API
# ============================================================

def index_pet(pet_id: int, description: str) -> None:
    """
    Encode a pet's description into a vector and upsert it into ChromaDB.

    Args:
        pet_id: The pet's database primary key.
        description: The pet's text description to embed.

    The document ID in ChromaDB is formatted as 'pet_{id}' to
    namespace it and avoid collisions with future collection types.
    """
    model = _get_model()
    collection = _get_collection()

    # Encode the description text into a 384-dimensional vector.
    embedding = model.encode(description).tolist()

    # Upsert: insert if new, update if pet_id already exists.
    collection.upsert(
        ids=[f"pet_{pet_id}"],
        embeddings=[embedding],
        documents=[description],
        metadatas=[{"pet_id": pet_id}],
    )
    print(f"[VECTOR] Indexed pet_{pet_id} into ChromaDB. Collection size: {collection.count()}")


def remove_pet(pet_id: int) -> None:
    """
    Remove a pet's vector from ChromaDB.
    Used when deactivating a pet from the matching engine.
    """
    collection = _get_collection()
    try:
        collection.delete(ids=[f"pet_{pet_id}"])
        print(f"[VECTOR] Removed pet_{pet_id} from ChromaDB. Collection size: {collection.count()}")
    except Exception:
        # If the ID doesn't exist, ChromaDB may raise or silently succeed
        # depending on the version. Either way, the pet is not indexed.
        print(f"[VECTOR] pet_{pet_id} was not in ChromaDB (already removed or never indexed).")


def query_matches(text: str, top_k: int = 5) -> list[dict]:
    """
    Encode query text and find the top-K most similar pet profiles.

    Args:
        text: The adopter's lifestyle description to match against.
        top_k: Maximum number of results to return.

    Returns:
        List of dicts with keys:
          - pet_id (int): The pet's database primary key
          - distance (float): ChromaDB L2 distance (lower = more similar)
          - similarity_score (float): Normalized 0-1 score (higher = better)
    """
    model = _get_model()
    collection = _get_collection()

    # If the collection is empty, return no matches.
    if collection.count() == 0:
        return []

    # Clamp top_k to actual collection size.
    actual_k = min(top_k, collection.count())

    query_embedding = model.encode(text).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=actual_k,
    )

    matches = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        # Convert L2 distance to a 0-1 similarity score.
        # L2 distance of 0 = identical, higher = less similar.
        # Using 1/(1+d) as a simple normalization.
        similarity = 1.0 / (1.0 + distance)

        matches.append({
            "pet_id": results["metadatas"][0][i]["pet_id"],
            "distance": distance,
            "similarity_score": round(similarity, 4),
        })

    # Sort by similarity descending (best match first).
    matches.sort(key=lambda m: m["similarity_score"], reverse=True)
    return matches
