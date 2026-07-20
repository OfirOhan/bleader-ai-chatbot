"""The retrieval-augmented chat brain.

answer() ties everything together for one user turn:
  1. translate the question to English and embed it,
  2. retrieve candidate review chunks with hybrid search (dense vectors + BM25),
     fuse the rankings (RRF) and rerank the pool with a cross-encoder,
  3. analyze the turn in one JSON call: update the running preference profile
     (the "gradually infer preferences" requirement) AND pick the reply language,
  4. generate an answer grounded ONLY in the retrieved chunks, in the user's
     language, and return it with source citations.
"""
from __future__ import annotations

from . import config, embeddings, lexical, llm, rerank, store, translate

# --- Prompts -----------------------------------------------------------------

ANSWER_SYSTEM = """\
You are AutoSage, a friendly, knowledgeable car-buying advisor.

Your knowledge comes ONLY from the review excerpts provided in each turn. They
are professional road-tests from the Israeli magazine auto.co.il. Treat them as
the entire extent of what you know about cars.

Rules:
- Ground every claim in the provided excerpts. Do not add specs, prices, history
  or comparisons from outside them, even for cars you happen to know well.
- If the excerpts do not answer the question — including when the user asks about
  a car you have no review for — say so plainly instead of guessing, and point to
  what you can help with. You may still relay what an excerpt says about another
  car it mentions, as long as you attribute it to that review rather than
  presenting it as your own knowledge of that car.
- Only offer to compare or recommend cars you actually have reviews for.
- Write your ENTIRE reply in the language named in REPLY LANGUAGE below. The
  excerpts are in Hebrew, but that must NOT change your reply language — follow
  REPLY LANGUAGE, not the language of the excerpts.
- Reply in plain text only. Do NOT use Markdown: no **bold**, no # headings, no
  `*` or `-` bullet lists. Separate ideas into short paragraphs with a blank line
  between them. The interface renders raw text, so any markup shows as literal
  characters.
- Be concise and conversational — a helpful advisor, not a spec sheet. Compare
  cars when useful and relate them to what you know of the user's preferences.
- Never mention "excerpts", "chunks", "context" or "embeddings"; just talk about
  the cars naturally.
"""

TURN_SYSTEM = """\
You analyze a car shopper's newest message. Return ONLY a JSON object with two
keys:

"reply_language": the language AutoSage should answer in — either "English" or
  "Hebrew". Honor an explicit request ("answer in Hebrew", "ענה באנגלית") even if
  the message itself is written in a different language; otherwise use the
  language the user wrote in.

"preferences": an updated copy of the running preference profile. Keep prior
  values unless the new message changes them; add newly revealed ones. Use only
  these keys, omitting any you have no signal for:
    budget        e.g. "under 120000 NIS"
    body_type     e.g. "supermini", "SUV", "sedan"
    powertrain    e.g. "EV", "hybrid", "gasoline", "manual"
    usage         e.g. "city commuting", "family", "long trips"
    priorities    array, e.g. ["comfort", "safety", "performance", "price"]
    candidates    array of car names the user is considering
"""


# --- Turn analysis: preferences + reply language (one call) ------------------

def _script_language(text: str) -> str:
    """Fallback: Hebrew if the text contains any Hebrew letter, else English."""
    if any("֐" <= ch <= "׿" for ch in text):
        return "Hebrew"
    return "English"


def analyze_turn(profile: dict, user_message: str) -> tuple[dict, str]:
    """Update the preference profile and choose the reply language in one call.

    Merging these (both are JSON extraction over the same message) saves a Gemini
    round-trip per turn. Falls back to script detection for the language and to
    the previous profile if the model returns anything unexpected.
    """
    payload = (
        f"Current preference profile:\n{profile}\n\n"
        f"User's newest message:\n{user_message}"
    )
    data = llm.generate_json(TURN_SYSTEM, payload)

    lang = str(data.get("reply_language", "")).strip().lower()
    if lang.startswith("he"):
        language = "Hebrew"
    elif lang.startswith("en"):
        language = "English"
    else:
        language = _script_language(user_message)

    prefs = data.get("preferences")
    new_profile = prefs if isinstance(prefs, dict) else profile
    return new_profile, language


# --- Retrieval: hybrid (dense + BM25) -> RRF -> cross-encoder rerank ----------

def _rrf(rankings: list[list[dict]], k_rrf: int = config.RRF_K) -> list[dict]:
    """Reciprocal Rank Fusion: merge several ranked lists into one.

    Each hit contributes 1 / (k_rrf + rank) to its id's score from every list it
    appears in, so a chunk ranked well by either retriever floats up. Ties on a
    single list are broken by the other retriever's opinion.
    """
    scores: dict[str, float] = {}
    hit_by_id: dict[str, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            hid = hit["id"]
            scores[hid] = scores.get(hid, 0.0) + 1.0 / (k_rrf + rank)
            hit_by_id.setdefault(hid, hit)
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [hit_by_id[hid] for hid in ordered]


def retrieve(question: str, k: int = config.TOP_K) -> tuple[list[dict], float]:
    """Hybrid retrieval for one question.

    Returns (top-k reranked hits, confidence) where confidence is the best
    cross-encoder relevance score — a much sharper "does the KB actually cover
    this?" signal than cosine, which is fooled when a review merely mentions an
    outside car.
    """
    query_en = translate.translate_query(question)

    dense = store.search(embeddings.embed_one(query_en), config.CANDIDATES)
    sparse = lexical.search(query_en, config.CANDIDATES)

    fused = _rrf([dense, sparse])[: config.RERANK_POOL]
    top = rerank.rerank(query_en, fused, k)

    confidence = top[0]["rerank_score"] if top else float("-inf")
    return top, confidence


def _format_context(hits: list[dict]) -> str:
    return "\n\n".join(f"### {h['car']}\n{h['text']}" for h in hits)


def _sources(hits: list[dict]) -> list[dict]:
    """Unique {car, url} in retrieval order — what the UI shows as citations."""
    seen, out = set(), []
    for h in hits:
        if h["car"] in seen:
            continue
        seen.add(h["car"])
        out.append({"car": h["car"], "url": h["url"]})
    return out


def _prefs_line(profile: dict) -> str:
    if not profile:
        return "No preferences inferred yet."
    parts = []
    for key in ("budget", "body_type", "powertrain", "usage"):
        if profile.get(key):
            parts.append(f"{key}: {profile[key]}")
    for key in ("priorities", "candidates"):
        vals = profile.get(key)
        if vals:
            parts.append(f"{key}: {', '.join(vals)}")
    return "; ".join(parts) if parts else "No preferences inferred yet."


# --- Main entry point --------------------------------------------------------

def answer(question: str, history: list[dict], profile: dict) -> dict:
    """Run one grounded turn.

    history: list of {role: 'user'|'assistant', content: str} (chronological).
    profile: the running preference dict for this conversation.
    Returns {content, sources, preferences}.
    """
    hits, confidence = retrieve(question)
    new_profile, language = analyze_turn(profile, question)

    convo = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in history[-config.MAX_HISTORY_TURNS:]
    )
    # Soft signal, not a hard cutoff: when nothing matched well, tell the model so
    # it leans on the "say you don't cover this" rule instead of forcing an answer.
    weak = confidence < config.RELEVANCE_FLOOR
    match_note = (
        "RETRIEVAL MATCH: weak — the reviews below may not actually cover this "
        "question. If they do not, say so instead of guessing.\n\n"
        if weak else ""
    )
    user_payload = (
        f"REPLY LANGUAGE: {language}\n\n"
        f"{match_note}"
        f"KNOWN USER PREFERENCES: {_prefs_line(new_profile)}\n\n"
        f"CONVERSATION SO FAR:\n{convo or '(none)'}\n\n"
        f"REVIEW EXCERPTS (your only source of truth):\n{_format_context(hits)}\n\n"
        f"USER QUESTION: {question}"
    )
    content = llm.generate_text(ANSWER_SYSTEM, user_payload)

    return {
        "content": content,
        "sources": _sources(hits),
        "preferences": new_profile,
    }
