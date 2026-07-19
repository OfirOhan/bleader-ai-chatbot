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
    """Translate many strings, filling and persisting the cache for misses."""
    cache = _load_cache()
    missing = [t for t in texts if _key(t) not in cache]
    if missing:
        # De-dupe before the API call.
        uniq = list(dict.fromkeys(missing))
        translated = llm.translate_he_to_en(uniq)
        for src, dst in zip(uniq, translated):
            cache[_key(src)] = dst
        _save_cache()
    return [cache[_key(t)] for t in texts]


def translate_query(text: str) -> str:
    """Translate one user query (cached like everything else)."""
    return translate_batch([text])[0]
