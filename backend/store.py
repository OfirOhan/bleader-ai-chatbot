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


def _hit(id_: str, doc: str, meta: dict, score: float) -> dict:
    return {
        "id": id_,
        "text": doc,                          # original Hebrew — used for grounding
        "text_en": meta.get("text_en", ""),   # English — used for BM25 / reranking
        "car": meta.get("car", "?"),
        "url": meta.get("url", ""),
        "score": round(float(score), 4),
    }


def search(query_embedding: list[float], k: int) -> list[dict]:
    """Return the top-k nearest chunks by vector similarity (score = cosine sim)."""
    res = collection().query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    # cosine distance -> similarity
    return [
        _hit(i, doc, meta, 1.0 - float(dist))
        for i, doc, meta, dist in zip(ids, docs, metas, dists)
    ]


def all_chunks() -> list[dict]:
    """Every stored chunk (no score) — used to build the lexical index."""
    res = collection().get(include=["documents", "metadatas"])
    ids = res.get("ids", [])
    docs = res.get("documents", [])
    metas = res.get("metadatas", [])
    return [_hit(i, doc, meta, 0.0) for i, doc, meta in zip(ids, docs, metas)]


def count() -> int:
    return collection().count()
