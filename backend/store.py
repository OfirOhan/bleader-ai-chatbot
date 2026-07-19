"""ChromaDB access — the local persistent vector store (assignment requirement).

Design choice: we embed the *English translation* of each chunk but keep the
*original Hebrew* as the stored document, because the answer should be grounded
in the real source text, not a lossy round-trip. So we pass embeddings in
explicitly rather than letting Chroma embed the documents itself.
"""
from __future__ import annotations

from functools import lru_cache

import chromadb

from . import config


@lru_cache(maxsize=1)
def collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset() -> None:
    """Drop and recreate the collection (used at the start of a full ingest)."""
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    collection.cache_clear()


def add(ids, documents, embeddings, metadatas) -> None:
    collection().add(
        ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
    )


def search(query_embedding: list[float], k: int) -> list[dict]:
    """Return the top-k chunks as flat dicts: text, car, url, score."""
    res = collection().query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    hits = []
    for doc, meta, dist in zip(docs, metas, dists):
        hits.append({
            "text": doc,
            "car": meta.get("car", "?"),
            "url": meta.get("url", ""),
            "score": round(1.0 - float(dist), 4),  # cosine distance -> similarity
        })
    return hits


def count() -> int:
    return collection().count()
