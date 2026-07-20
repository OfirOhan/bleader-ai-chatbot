"""Cross-encoder reranking.

Dense + BM25 retrieval is fast but approximate: it scores the query and each
chunk independently. A cross-encoder reads the (query, chunk) pair together and
scores their actual relevance, which is far more precise — so we over-retrieve a
pool, then keep the best TOP_K after reranking.

The model (ms-marco-MiniLM, English-trained) runs on the English chunk text and
is loaded lazily + cached (first call downloads ~80 MB of weights).
"""
from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(config.RERANK_MODEL)


def rerank(query_en: str, hits: list[dict], k: int) -> list[dict]:
    """Return the k most relevant hits, ordered, with a `rerank_score` attached."""
    if not hits:
        return []
    scores = _model().predict([(query_en, h["text_en"]) for h in hits])
    order = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order[:k]:
        hit = dict(hits[i])
        hit["rerank_score"] = float(scores[i])
        out.append(hit)
    return out
