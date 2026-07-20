"""Lexical (BM25) retrieval over the English chunk text.

Dense vector search blurs exact tokens — car model names, trims, and spec
numbers ("RS3", "GV80", "670", "Nappa") — especially since our vectors are built
from a Hebrew->English translation. BM25 keyword matching recovers those exact
hits, and we fuse the two rankings (see rag._rrf) so each covers the other's
blind spot.

The index is built once from ChromaDB and cached for the process lifetime.
"""
from __future__ import annotations

import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from . import store

_WORD = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


@lru_cache(maxsize=1)
def _index() -> tuple[BM25Okapi, list[dict]]:
    chunks = store.all_chunks()
    corpus = [_tokenize(c["text_en"]) for c in chunks]
    return BM25Okapi(corpus), chunks


def search(query_en: str, k: int) -> list[dict]:
    """Top-k chunks by BM25 over the English query. Empty if nothing is indexed."""
    bm25, chunks = _index()
    if not chunks:
        return []
    scores = bm25.get_scores(_tokenize(query_en))
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    hits = []
    for i in order[:k]:
        hit = dict(chunks[i])
        hit["score"] = round(float(scores[i]), 4)
        hits.append(hit)
    return hits


def reset_cache() -> None:
    _index.cache_clear()
