"""Hand-labeled evaluation set for AutoSage.

Small on purpose — 8 cars, so ground truth is exact and cheap to label. Used by:
  - retrieval_eval.py : does the retriever surface the right car? (hit@k, MRR)
  - gate_eval / tests : are out-of-scope questions flagged as weak matches?
  - faithfulness_eval.py : is the generated answer grounded? (local LLM judge)

`expected` is the car name(s) the question is about, matching the `car` metadata
in the store exactly. Out-of-scope questions have expected=[] and in_scope=False:
there is no review for them, so the system should decline, not answer.

Questions are in English (the space the retriever operates in) so retrieval eval
needs no translation call and stays free.
"""
from __future__ import annotations

# Easy in-scope: the question names the car. Picking 1 of 8 is trivial, so every
# retriever should ace these — they're a sanity floor, not a discriminator.
NAMED = [
    ("How is the Genesis GV80 interior quality?",        ["Genesis GV80 (2026)"]),
    ("Is the Hyundai Elantra N fun with the manual box?", ["Hyundai Elantra N (manual)"]),
    ("Tell me about the Kia EV9 as a long-term daily car", ["Kia EV9 (long-term report)"]),
    ("What is the trunk capacity of the Aion HT?",       ["Aion HT"]),
    ("How does the Citroen C3 ride comfort feel?",       ["Citroën C3 (2026)"]),
    ("What engine does the Audi RS3 have?",              ["Audi RS3 (facelift)"]),
    ("Is the MG S6 a good electric SUV?",                ["MG S6"]),
    ("Tell me about the Lynk & Co 01 plug-in hybrid",    ["Lynk & Co 01 (2026)"]),
]

# Hard in-scope: the car is NOT named — it must be found from a distinctive
# feature, spec, or number. This is where dense retrieval can grab the wrong car
# and BM25 (exact tokens like "670", "five-cylinder") + reranking pull it back.
FEATURE = [
    ("Which car here has a 27-inch curved display?",        ["Genesis GV80 (2026)"]),
    ("Which model is offered with a manual gearbox?",       ["Hyundai Elantra N (manual)"]),
    ("Which one uses hydraulic cushions in its suspension?", ["Citroën C3 (2026)"]),
    ("Which car has a five-cylinder engine?",               ["Audi RS3 (facelift)"]),
    ("Which SUV has a 670 liter trunk?",                    ["Aion HT"]),
    ("Which of these is a plug-in hybrid?",                 ["Lynk & Co 01 (2026)"]),
    ("Which car offers a third row with seven seats?",
     ["Kia EV9 (long-term report)", "Genesis GV80 (2026)"]),
]

IN_SCOPE = NAMED + FEATURE

# Out-of-scope: no review exists — the system must decline, not answer.
OUT_OF_SCOPE = [
    "Tell me about the Toyota Corolla reliability",
    "What is the range and price of the Tesla Model Y?",
    "How does the BMW X5 compare to the Volvo XC90?",
    "What is the best pizza recipe?",
]


def in_scope_cases() -> list[dict]:
    named = [{"q": q, "expected": e, "in_scope": True, "group": "named"}
             for q, e in NAMED]
    feature = [{"q": q, "expected": e, "in_scope": True, "group": "feature"}
               for q, e in FEATURE]
    return named + feature


def all_cases() -> list[dict]:
    out = in_scope_cases()
    out += [{"q": q, "expected": [], "in_scope": False, "group": "out"}
            for q in OUT_OF_SCOPE]
    return out
