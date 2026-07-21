"""Hebrew->English translation with a persistent on-disk cache.

Ingest translates every chunk once; the cache (keyed by a content hash) means
re-running ingest, or embedding overlapping text, never pays for the same
translation twice. Query-time translation of the user's question reuses the same
path so the query lands in the same English vector space as the corpus.
"""
from __future__ import annotations

import hashlib
import json

from . import config, llm

_cache: dict[str, str] | None = None


def _load_cache() -> dict[str, str]:
    global _cache
    if _cache is None:
        if config.TRANSLATION_CACHE.exists():
            _cache = json.loads(config.TRANSLATION_CACHE.read_text(encoding="utf-8"))
        else:
            _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is not None:
        config.TRANSLATION_CACHE.write_text(
            json.dumps(_cache, ensure_ascii=False, indent=0), encoding="utf-8"
        )


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def translate_batch(texts: list[str]) -> list[str]:
    """Translate many strings, persisting only successful translations.

    A translation that came back unchanged (== source) is a failed fallback —
    we return it for this run but do NOT cache it, so re-running ingest retries it
    instead of permanently serving untranslated Hebrew.
    """
    cache = _load_cache()
    fresh: dict[str, str] = {}
    missing = [t for t in texts if _key(t) not in cache]
    if missing:
        uniq = list(dict.fromkeys(missing))  # de-dupe before the API call
        translated = llm.translate_he_to_en(uniq)
        changed = False
        for src, dst in zip(uniq, translated):
            fresh[src] = dst
            if dst and dst != src:           # only persist real translations
                cache[_key(src)] = dst
                changed = True
        if changed:
            _save_cache()
    return [cache.get(_key(t)) or fresh.get(t) or t for t in texts]


def translate_query(text: str) -> str:
    """Translate one user query to English for retrieval (cached).

    Uses the dedicated query translator, not the passage translator — a query
    must be translated faithfully, not elaborated. Cache keys are namespaced
    ("q:") so a query never collides with a same-text document chunk.
    """
    cache = _load_cache()
    key = "q:" + _key(text)
    if key not in cache:
        cache[key] = llm.translate_query_to_en(text)
        _save_cache()
    return cache[key]
