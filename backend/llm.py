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


def translate_he_to_en(texts: list[str]) -> list[str]:
    """Translate a batch of Hebrew strings to English in one call.

    Returns the translations in the same order. Falls back to the originals if
    the model returns an unexpected shape (so ingest never hard-fails on a
    translation hiccup — retrieval just degrades gracefully to Hebrew text).
    """
    if not texts:
        return []
    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    system = (
        "You are a professional automotive translator. Translate each numbered "
        "Hebrew passage to natural English, preserving car names, numbers, units "
        "and technical terms. Return a JSON object mapping the string index to "
        'its English translation, e.g. {"0": "...", "1": "..."}. Indices only, '
        "no extra keys."
    )
    data = generate_json(system, numbered)
    out: list[str] = []
    for i, original in enumerate(texts):
        val = data.get(str(i))
        out.append(val if isinstance(val, str) and val.strip() else original)
    return out
