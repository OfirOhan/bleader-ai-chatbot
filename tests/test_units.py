"""Pure-function unit tests — no models, no API, fast."""
from __future__ import annotations

from backend import corpus, rag


def test_chunk_text_respects_size_and_overlaps():
    text = "\n\n".join(f"Paragraph number {i} " + "word " * 40 for i in range(6))
    chunks = corpus.chunk_text(text, size=300, overlap=50)
    assert len(chunks) > 1
    # Nothing wildly over the target (size + one overlap slack).
    assert all(len(c) <= 300 + 50 for c in chunks)
    # Consecutive chunks share text (overlap) — some tail of one appears in the next.
    assert any(chunks[i][-20:] in chunks[i + 1] for i in range(len(chunks) - 1))


def test_rrf_rewards_agreement():
    a = [{"id": "x"}, {"id": "y"}, {"id": "z"}]
    b = [{"id": "y"}, {"id": "w"}, {"id": "x"}]
    fused = [h["id"] for h in rag._rrf([a, b])]
    # y is top-ranked in one list and 1st in the other -> should lead.
    assert fused[0] == "y"
    # x appears in both -> should beat z/w that appear once.
    assert fused.index("x") < fused.index("z")
    assert fused.index("x") < fused.index("w")


def test_sources_dedupe_preserves_order():
    hits = [
        {"car": "MG S6", "url": "u1"},
        {"car": "Aion HT", "url": "u2"},
        {"car": "MG S6", "url": "u1"},
    ]
    src = rag._sources(hits)
    assert [s["car"] for s in src] == ["MG S6", "Aion HT"]


def test_script_language_detection():
    assert rag._script_language("How is the Kia EV9?") == "English"
    assert rag._script_language("ספר לי על הקיה") == "Hebrew"
    # Mixed with any Hebrew letter counts as Hebrew.
    assert rag._script_language("EV9 טוב?") == "Hebrew"
