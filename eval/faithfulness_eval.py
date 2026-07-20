"""Generation-faithfulness evaluation with a LOCAL LLM judge.

Retrieval eval (retrieval_eval.py) needs no judge. This one does: it grades
whether the *generated answer* is grounded in the retrieved reviews, or whether
it hallucinated — the RAGAS-style "faithfulness" metric. Using a separate local
model as the judge keeps it independent of Gemini (the generator) and free.

The judge is any OpenAI-compatible chat endpoint — e.g. a Qwen model served by
vLLM, Ollama, or LM Studio. Point it with env vars:

    JUDGE_BASE_URL   default http://localhost:8000/v1   (Ollama: .../11434/v1)
    JUDGE_MODEL      default Qwen/Qwen2.5-7B-Instruct

Run (needs GEMINI_API_KEY for generation + a reachable judge):

    uv run python -m eval.faithfulness_eval          # all questions
    uv run python -m eval.faithfulness_eval --limit 4

Reports, over in-scope questions, mean groundedness (1-5) and hallucination
rate; over out-of-scope questions, how often the system correctly declined.
"""
from __future__ import annotations

import argparse
import json
import os

import requests

from backend import rag
from eval.dataset import all_cases

JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "http://localhost:8000/v1").rstrip("/")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-7B-Instruct")

JUDGE_SYSTEM = (
    "You are a strict evaluator of a car-advice assistant. You are given a "
    "QUESTION, the CONTEXT passages the assistant was allowed to use, and its "
    "ANSWER. Judge ONLY whether the answer is supported by the context — not "
    "whether it sounds good. Return ONLY JSON: "
    '{"grounded": <1-5, how well every claim is supported by the context>, '
    '"hallucinated": <true if it states specs/prices/facts not in the context>, '
    '"refused": <true if the answer says it has no review/data for the specific '
    "car or topic asked — this still counts as true even if it then suggests "
    'other cars it does have information on>}.'
)


def _judge(question: str, context: str, answer: str) -> dict:
    payload = {
        "model": JUDGE_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content":
                f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"},
        ],
    }
    resp = requests.post(
        f"{JUDGE_BASE_URL}/chat/completions", json=payload, timeout=120
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def _context_for(question: str) -> str:
    hits, _ = rag.retrieve(question)
    return "\n\n".join(f"[{h['car']}] {h['text_en']}" for h in hits)


def run(limit: int | None = None) -> None:
    cases = all_cases()
    if limit:
        # keep a mix of in- and out-of-scope
        cases = cases[:limit] + [c for c in cases if not c["in_scope"]][:2]

    grounded_scores, halluc_flags = [], []
    refusals_correct = refusals_total = 0

    for c in cases:
        q = c["q"]
        context = _context_for(q)
        answer = rag.answer(q, [], {})["content"]
        try:
            v = _judge(q, context, answer)
        except Exception as exc:  # noqa: BLE001
            print(f"  judge error on {q!r}: {exc}")
            continue

        tag = "in " if c["in_scope"] else "out"
        print(f"[{tag}] grounded={v.get('grounded')} "
              f"halluc={v.get('hallucinated')} refused={v.get('refused')}  {q}")

        if c["in_scope"]:
            if isinstance(v.get("grounded"), (int, float)):
                grounded_scores.append(float(v["grounded"]))
            halluc_flags.append(bool(v.get("hallucinated")))
        else:
            refusals_total += 1
            refusals_correct += bool(v.get("refused"))

    print("\n--- faithfulness summary ---")
    if grounded_scores:
        mean = sum(grounded_scores) / len(grounded_scores)
        rate = sum(halluc_flags) / len(halluc_flags)
        print(f"in-scope mean groundedness: {mean:.2f} / 5  (n={len(grounded_scores)})")
        print(f"in-scope hallucination rate: {rate:.0%}")
    if refusals_total:
        print(f"out-of-scope correctly declined: "
              f"{refusals_correct}/{refusals_total}")
    print(f"(judge: {JUDGE_MODEL} @ {JUDGE_BASE_URL})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap number of questions (cheaper run)")
    run(ap.parse_args().limit)
