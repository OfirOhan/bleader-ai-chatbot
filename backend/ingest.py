"""Build the knowledge base.

    python -m backend.ingest            # fetch (cached) + chunk + translate + embed
    python -m backend.ingest --refresh  # re-download the articles from the web

Pipeline per article:
    fetch HTML  ->  extract main text  ->  chunk  ->  translate chunk to English
    ->  embed English with MiniLM  ->  store {Hebrew doc, English-based vector}
    in ChromaDB with {car, url} metadata.
"""
from __future__ import annotations

import argparse
import sys

from . import config, corpus, embeddings, store, translate


def run(refresh: bool = False) -> None:
    print(f"Building knowledge base for {len(corpus.ARTICLES)} articles...\n")
    store.reset()

    total = 0
    for art in corpus.ARTICLES:
        try:
            text = corpus.load_article_text(art, refresh=refresh)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {art.name}: failed to load ({exc}) — skipping")
            continue

        chunks = corpus.chunk_text(text)
        if not chunks:
            print(f"  ! {art.name}: no text extracted — skipping")
            continue

        english = translate.translate_batch(chunks)   # cached
        vectors = embeddings.embed(english)

        ids = [f"{art.slug}-{i}" for i in range(len(chunks))]
        # Keep the English translation alongside the Hebrew document: the lexical
        # (BM25) index and the cross-encoder reranker both operate in English.
        metas = [
            {"car": art.name, "url": art.url, "lang": "he", "text_en": en}
            for en in english
        ]
        store.add(ids=ids, documents=chunks, embeddings=vectors, metadatas=metas)

        total += len(chunks)
        print(f"  ✓ {art.name}: {len(chunks)} chunks")

    print(f"\nDone. {total} chunks indexed in ChromaDB at {config.CHROMA_DIR}")


def main() -> None:
    # Windows consoles default to cp1252 and crash on the ✓ progress glyphs;
    # force UTF-8 so ingest output is portable.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Ingest car road-test articles.")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download articles instead of using the cache")
    args = ap.parse_args()
    if not config.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set (needed for translation). "
              "See .env.example.", file=sys.stderr)
        sys.exit(1)
    run(refresh=args.refresh)


if __name__ == "__main__":
    main()
