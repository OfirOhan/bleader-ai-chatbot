"""Embedding model: sentence-transformers/all-MiniLM-L6-v2 (assignment option B).

MiniLM is English-trained, so the corpus (Hebrew) and queries are translated to
English *before* they reach this module — see translate.py / rag.py. This keeps
the vector space monolingual and retrieval quality high, which is the whole
point of the translate-at-ingest trade-off.

The model is loaded lazily and cached: the first call downloads ~90 MB of
weights, subsequent calls are instant.
"""
from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    """Return L2-normalized embeddings for a list of (English) texts."""
    if not texts:
        return []
    vecs = _model().encode(
        texts,
        normalize_embeddings=True,   # cosine similarity via inner product
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vecs.tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
