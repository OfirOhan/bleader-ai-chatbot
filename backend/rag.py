"""The retrieval-augmented chat brain.

answer() ties everything together for one user turn:
  1. translate the question to English and embed it,
  2. retrieve the most relevant Hebrew review chunks from ChromaDB,
  3. update the running user-preference profile (the "gradually infer
     preferences" requirement),
  4. generate an answer grounded ONLY in the retrieved chunks, in the user's
     language, and return it with source citations.
"""
from __future__ import annotations

from . import config, embeddings, llm, store, translate

# --- Prompts -----------------------------------------------------------------

ANSWER_SYSTEM = """\
You are AutoSage, a friendly, knowledgeable car-buying advisor.

Your knowledge comes ONLY from the review excerpts provided in each turn. These
are professional road-tests from the Israeli magazine auto.co.il.

Rules:
- Ground every claim in the provided excerpts. Do NOT invent specs, prices or
  facts that are not supported by them.
- If the excerpts do not cover the question, say so plainly and suggest what the
  user could ask about instead (the cars you *do* have reviews for).
- Reply in the SAME language the user wrote in (Hebrew or English).
- Be concise and conversational — a helpful advisor, not a spec sheet. Compare
  cars when useful and relate them to what you know of the user's preferences.
- Never mention "excerpts", "chunks", "context" or "embeddings"; just talk about
  the cars naturally.
"""

PREF_SYSTEM = """\
You maintain a compact profile of a car shopper's preferences, inferred from the
conversation so far. Given the current profile (JSON) and the user's newest
message, return an UPDATED profile as a JSON object. Keep prior values unless the
new message changes them; add newly revealed ones.

Use these keys (omit any you have no signal for):
  budget            e.g. "under 120000 NIS"
  body_type         e.g. "supermini", "SUV", "sedan"
  powertrain        e.g. "EV", "hybrid", "gasoline", "manual"
  usage             e.g. "city commuting", "family", "long trips"
  priorities        array, e.g. ["comfort", "safety", "performance", "price"]
  candidates        array of car names the user is considering
Return ONLY the JSON object.
"""


# --- Retrieval ---------------------------------------------------------------

def retrieve(question: str, k: int = config.TOP_K) -> list[dict]:
    query_en = translate.translate_query(question)
    vec = embeddings.embed_one(query_en)
    return store.search(vec, k)


def _format_context(hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        blocks.append(f"### {h['car']}\n{h['text']}")
    return "\n\n".join(blocks)


def _sources(hits: list[dict]) -> list[dict]:
    """Unique {car, url} in retrieval order — what the UI shows as citations."""
    seen, out = set(), []
    for h in hits:
        if h["car"] in seen:
            continue
        seen.add(h["car"])
        out.append({"car": h["car"], "url": h["url"]})
    return out


# --- Preference inference ----------------------------------------------------

def update_preferences(profile: dict, user_message: str) -> dict:
    payload = (
        f"Current profile:\n{profile}\n\nUser's newest message:\n{user_message}"
    )
    updated = llm.generate_json(PREF_SYSTEM, payload)
    return updated or profile


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
    hits = retrieve(question)
    new_profile = update_preferences(profile, question)

    convo = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in history[-config.MAX_HISTORY_TURNS:]
    )
    user_payload = (
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
