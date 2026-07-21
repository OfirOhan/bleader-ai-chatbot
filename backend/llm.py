"""Thin wrapper around the Gemini client (google-genai).

Kept tiny and dependency-light so the rest of the code talks to a stable
interface: `generate_text()` for prose and `generate_json()` for structured
extraction (preference inference).
"""
from __future__ import annotations

import json
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _client():
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    from google import genai

    return genai.Client(api_key=config.GEMINI_API_KEY)


def generate_text(system: str, user: str, *, temperature: float = 0.3) -> str:
    """Single-shot generation. `system` is the instruction, `user` the payload."""
    from google.genai import types

    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        ),
    )
    return (resp.text or "").strip()


def generate_json(system: str, user: str, *, temperature: float = 0.0) -> dict:
    """Generation constrained to a JSON object. Returns {} on parse failure."""
    from google.genai import types

    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    raw = (resp.text or "").strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def translate_query_to_en(text: str) -> str:
    """Faithfully translate one short user query to English for retrieval.

    Distinct from translate_he_to_en (which translates document passages): a
    query may already be English and may contain instructions like "answer in
    Hebrew" — it must be *translated verbatim*, never answered or elaborated.
    Reusing the passage translator here caused it to hallucinate a spec sheet
    instead of translating, which broke retrieval.
    """
    system = (
        "You translate a short car-shopping search query into English. Output "
        "ONLY the translated query text — never answer it, never add facts or "
        "descriptions, never explain. If it is already English, return it "
        "unchanged. Preserve car names, model codes, numbers and units exactly."
    )
    return generate_text(system, text, temperature=0.0).strip()


_TRANSLATE_SYSTEM = (
    "You are a professional automotive translator. Translate each numbered "
    "Hebrew passage to natural English, preserving car names, numbers, units "
    "and technical terms. Return a JSON object mapping the string index to "
    'its English translation, e.g. {"0": "...", "1": "..."}. Indices only, '
    "no extra keys."
)


def translate_he_to_en(texts: list[str], *, batch_size: int = 8) -> list[str]:
    """Translate Hebrew passages to English, in small retried batches.

    Small batches keep each JSON response well under the output-token limit — a
    large batch could be truncated into invalid JSON, which silently fell back to
    untranslated Hebrew and broke retrieval for a whole article. Missing indices
    are retried (with a little temperature to escape a deterministic bad parse);
    anything still missing falls back to the original, and the caller declines to
    cache such fallbacks so a later run can heal them.
    """
    if not texts:
        return []
    out: list[str] = []
    for start in range(0, len(texts), batch_size):
        out.extend(_translate_group(texts[start:start + batch_size]))
    return out


def _translate_group(texts: list[str]) -> list[str]:
    result: list[str | None] = [None] * len(texts)
    pending = list(range(len(texts)))
    for attempt in range(3):
        if not pending:
            break
        numbered = "\n".join(f"[{i}] {texts[i]}" for i in pending)
        data = generate_json(
            _TRANSLATE_SYSTEM, numbered, temperature=0.0 if attempt == 0 else 0.4
        )
        still: list[int] = []
        for i in pending:
            val = data.get(str(i))
            if isinstance(val, str) and val.strip():
                result[i] = val.strip()
            else:
                still.append(i)
        pending = still
    for i in pending:  # retries exhausted — keep original (heals on next ingest)
        result[i] = texts[i]
    return result  # type: ignore[return-value]
