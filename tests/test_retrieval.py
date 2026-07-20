"""Retrieval-behavior tests. Local models only (no Gemini); skipped if the
knowledge base hasn't been ingested yet."""
from __future__ import annotations

import pytest

from backend import config, embeddings, lexical, rag, rerank, store

pytestmark = pytest.mark.skipif(
    store.count() == 0, reason="knowledge base not ingested (run: python -m backend.ingest)"
)


def _confidence(question_en: str) -> float:
    dense = store.search(embeddings.embed_one(question_en), config.CANDIDATES)
    fused = rag._rrf([dense, lexical.search(question_en, config.CANDIDATES)])
    top = rerank.rerank(question_en, fused[: config.RERANK_POOL], config.TOP_K)
    return top[0]["rerank_score"] if top else float("-inf")


def test_bm25_finds_exact_spec_tokens():
    # A distinctive number/term should lexically pin the right car.
    assert lexical.search("670 liter trunk", 5)[0]["car"] == "Aion HT"
    assert lexical.search("five-cylinder engine", 5)[0]["car"] == "Audi RS3 (facelift)"


def test_gate_separates_in_scope_from_out_of_scope():
    in_scope = _confidence("How is the Genesis GV80 interior?")
    off_topic = _confidence("What is the best pizza recipe?")
    assert in_scope > config.RELEVANCE_FLOOR
    assert off_topic < config.RELEVANCE_FLOOR
    # And by a clear margin, not a coin flip.
    assert in_scope - off_topic > 3.0
