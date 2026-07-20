"""Retrieval + gate evaluation — fully local, no API calls, no LLM judge.

Retrieval quality is measured against labeled ground truth (which car each
question is about), so it needs no model to grade it:

    uv run python -m eval.retrieval_eval

Reports hit@1, hit@3 and MRR for three retrievers — dense-only, hybrid
(dense+BM25 via RRF), and hybrid+cross-encoder rerank — so the effect of each
stage is visible. Then reports the relevance gate's accuracy at telling in-scope
from out-of-scope questions.

Questions are English (the retriever's space), so no translation call is made.
"""
from __future__ import annotations

from backend import config, embeddings, lexical, rag, rerank, store
from eval.dataset import all_cases, in_scope_cases


def _car_ranking(hits: list[dict]) -> list[str]:
    """Collapse chunk hits to the order in which distinct cars first appear."""
    ranking: list[str] = []
    for h in hits:
        if h["car"] not in ranking:
            ranking.append(h["car"])
    return ranking


def _rank_of(ranking: list[str], expected: list[str]) -> int | None:
    for i, car in enumerate(ranking, start=1):
        if car in expected:
            return i
    return None


def _metrics(rankings_and_expected: list[tuple[list[str], list[str]]]) -> dict:
    n = len(rankings_and_expected)
    hit1 = hit3 = 0
    mrr = 0.0
    for ranking, expected in rankings_and_expected:
        r = _rank_of(ranking, expected)
        if r is not None:
            hit1 += r <= 1
            hit3 += r <= 3
            mrr += 1.0 / r
    return {"hit@1": hit1 / n, "hit@3": hit3 / n, "MRR": mrr / n}


def run() -> None:
    # rankings per config, split by difficulty group; gate = list of (case, conf)
    rk = {g: {"dense": [], "hybrid": [], "rerank": []} for g in ("named", "feature")}
    gate = []

    for c in all_cases():
        q = c["q"]
        dense = store.search(embeddings.embed_one(q), config.CANDIDATES)
        sparse = lexical.search(q, config.CANDIDATES)
        fused = rag._rrf([dense, sparse])
        reranked = rerank.rerank(q, fused[: config.RERANK_POOL], config.TOP_K)

        confidence = reranked[0]["rerank_score"] if reranked else float("-inf")
        gate.append((c, confidence))

        if c["in_scope"]:
            g = rk[c["group"]]
            g["dense"].append((_car_ranking(dense), c["expected"]))
            g["hybrid"].append((_car_ranking(fused), c["expected"]))
            g["rerank"].append((_car_ranking(reranked), c["expected"]))

    for group, title in [("named", "Easy: question names the car"),
                         ("feature", "Hard: car found from a feature/spec only")]:
        n = len(rk[group]["dense"])
        print(f"\n{title}  (n={n})")
        print(f"{'retriever':<22}{'hit@1':>8}{'hit@3':>8}{'MRR':>8}")
        for key, label in [("dense", "dense (vector only)"),
                           ("hybrid", "hybrid (dense+BM25)"),
                           ("rerank", "hybrid + rerank")]:
            m = _metrics(rk[group][key])
            print(f"{label:<22}{m['hit@1']:>8.2f}{m['hit@3']:>8.2f}{m['MRR']:>8.2f}")

    # Gate: in-scope should clear the floor; out-of-scope should fall below it.
    floor = config.RELEVANCE_FLOOR
    tp = [c for c, v in gate if c["in_scope"] and v >= floor]
    fn = [c for c, v in gate if c["in_scope"] and v < floor]
    tn = [c for c, v in gate if not c["in_scope"] and v < floor]
    fp = [(c, v) for c, v in gate if not c["in_scope"] and v >= floor]
    print(f"\nRelevance gate (floor = {floor}, confidence = top rerank score)")
    print(f"  in-scope kept (answered):   {len(tp)}/{len(tp) + len(fn)}")
    print(f"  out-of-scope flagged weak:  {len(tn)}/{len(tn) + len(fp)}")
    for c, v in fp:
        print(f"  ! slipped through ({v:+.2f}): {c['q']}")
    for c in fn:
        print(f"  ! in-scope wrongly flagged: {c['q']}")


if __name__ == "__main__":
    run()
