"""
ChromaDB persistent client setup and embedding of the café log.
Matches the course gateway pattern used in the labs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "cafe_log.jsonl"
PERSIST_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "gustopins_cafe_log"

# Course API Gateway (from labs)
GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"


def get_embedding_function():
    """
    OpenAI embedding function that follows the course gateway pattern.
    """
    gateway_key = os.getenv("API_GATEWAY_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    use_gateway = bool(gateway_key and gateway_key.strip() and not gateway_key.strip().lower().startswith("if "))
    if os.getenv("USE_GATEWAY", "").lower() in ("true", "1", "yes"):
        use_gateway = True

    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    if use_gateway:
        print("[GustoPins embeddings] Using course API Gateway")
        print(f"[GustoPins embeddings] base URL: {GATEWAY_BASE_URL}")
        return OpenAIEmbeddingFunction(
            api_key="any value",  # required by the SDK but ignored by the gateway
            api_base=GATEWAY_BASE_URL,
            api_type="openai",
            model_name=model_name,
            default_headers={"x-api-key": gateway_key},
        )
    else:
        print("[GustoPins embeddings] Using direct OpenAI key")
        return OpenAIEmbeddingFunction(
            api_key=openai_key or "dummy",
            model_name=model_name,
        )


def build_or_load_collection(force_rebuild: bool = False):
    """
    Create a persistent Chroma collection and load the café log if needed.
    Returns the collection object.
    """
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    embedding_fn = get_embedding_function()

    existing = [c.name for c in client.list_collections()]

    if COLLECTION_NAME in existing and not force_rebuild:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
        if collection.count() > 0:
            return collection
        client.delete_collection(COLLECTION_NAME)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Café log not found at {DATA_PATH}")

    documents = []
    metadatas = []
    ids = []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            doc_text = (
                f"{rec.get('name', '')}. "
                f"{rec.get('type', '')} in {rec.get('neighbourhood', '')}, {rec.get('city', 'Toronto')}. "
                f"Status: {rec.get('status', '')}. "
                f"Vibe: {rec.get('vibe', '')}. "
                f"Notes: {rec.get('notes', '')}. "
                f"Tags: {', '.join(rec.get('tags', []))}."
            )
            documents.append(doc_text)
            metadatas.append(
                {
                    "name": rec.get("name", ""),
                    "neighbourhood": rec.get("neighbourhood", ""),
                    "city": rec.get("city", "Toronto"),
                    "type": rec.get("type", ""),
                    "status": rec.get("status", ""),
                    "vibe": rec.get("vibe", ""),
                    "notes": rec.get("notes", ""),
                    "address": rec.get("address", ""),
                }
            )
            ids.append(rec.get("id") or rec.get("name", "").lower().replace(" ", "-"))

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "GustoPins personal café and restaurant log"},
    )

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return collection
