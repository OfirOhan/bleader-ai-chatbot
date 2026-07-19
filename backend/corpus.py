"""The source corpus: the 8 auto.co.il road-test articles, plus helpers to
fetch, cache and clean them into plain text.

Extraction strategy: try `trafilatura` (very good at isolating the main article
body from navigation/ads/comments), and fall back to a BeautifulSoup heuristic.
Raw HTML and cleaned text are cached under backend/data so re-ingesting is
offline and fast.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import requests

from . import config

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass(frozen=True)
class Article:
    slug: str          # cache filename + stable id prefix
    name: str          # human label shown as the source / citation
    url: str


# The assignment's 8 primary sources.
ARTICLES: list[Article] = [
    Article("citroen-c3-2026", "Citroën C3 (2026)",
            "https://www.auto.co.il/articles/test-drives/road-tests/citroen-c3-2026/"),
    Article("audi-rs3-fl", "Audi RS3 (facelift)",
            "https://www.auto.co.il/articles/test-drives/road-tests/audi-rs3-fl/"),
    Article("kia-ev9-long-term", "Kia EV9 (long-term report)",
            "https://www.auto.co.il/articles/test-drives/road-tests/long-term-report-kia-ev9-4/"),
    Article("mg-s6", "MG S6",
            "https://www.auto.co.il/articles/test-drives/road-tests/mg-s6/"),
    Article("hyundai-elantra-n-manual", "Hyundai Elantra N (manual)",
            "https://www.auto.co.il/articles/test-drives/road-tests/hyundai-elantra-n-manual/"),
    Article("aion-ht", "Aion HT",
            "https://www.auto.co.il/articles/test-drives/road-tests/aion-ht/"),
    Article("lynk-co-01-2026", "Lynk & Co 01 (2026)",
            "https://www.auto.co.il/articles/test-drives/road-tests/link-and-co-01-2026/"),
    Article("genesis-gv80-2026", "Genesis GV80 (2026)",
            "https://www.auto.co.il/articles/test-drives/road-tests/genesis-gv80-2026/"),
]


def _fetch_html(article: Article, *, refresh: bool = False) -> str:
    """Return the article HTML, using a local cache unless `refresh`."""
    cache = config.RAW_DIR / f"{article.slug}.html"
    if cache.exists() and not refresh:
        return cache.read_text(encoding="utf-8")
    resp = requests.get(article.url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text


def _extract_text(html: str) -> str:
    """Isolate the main article text from a full HTML page."""
    # Primary: trafilatura.
    try:
        import trafilatura

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        if text and len(text) > 400:
            return text
    except Exception:
        pass

    # Fallback: strip scripts/styles and take visible text from <article>/<main>.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    return root.get_text("\n")


def _tidy(text: str) -> str:
    """Collapse whitespace and drop obvious boilerplate lines."""
    lines: list[str] = []
    seen: set[str] = set()
    junk = ("צילום:", "לייעוץ חינם", "לקבלת הצעת מחיר", "הצטרפו", "וואטסאפ",
            "WhatsApp", "http://", "https://", "צריכים יעוץ")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) < 2:
            continue
        if any(j in line for j in junk):
            continue
        if line in seen:  # de-dupe repeated captions / CTAs
            continue
        seen.add(line)
        lines.append(line)
    out = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def load_article_text(article: Article, *, refresh: bool = False) -> str:
    """Fetch + extract + tidy one article, caching the cleaned text."""
    clean_cache = config.CLEAN_DIR / f"{article.slug}.txt"
    if clean_cache.exists() and not refresh:
        return clean_cache.read_text(encoding="utf-8")
    html = _fetch_html(article, refresh=refresh)
    text = _tidy(_extract_text(html))
    clean_cache.write_text(text, encoding="utf-8")
    return text


def chunk_text(text: str, *, size: int = config.CHUNK_CHARS,
               overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Paragraph-aware character chunking with overlap.

    Paragraphs are packed together up to `size`; anything longer than `size` on
    its own is hard-split. Consecutive chunks share `overlap` characters so a
    fact that straddles a boundary is still retrievable.
    """
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paras:
        if len(buf) + len(para) + 2 <= size:
            buf = f"{buf}\n\n{para}" if buf else para
            continue
        if buf:
            chunks.append(buf)
        if len(para) <= size:
            buf = para
        else:  # a single very long paragraph — hard split
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i:i + size])
            buf = ""
    if buf:
        chunks.append(buf)

    # Add overlap between adjacent chunks for retrieval robustness.
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for prev, cur in zip(chunks, chunks[1:]):
            tail = prev[-overlap:]
            overlapped.append(f"{tail} {cur}")
        chunks = overlapped
    return [c.strip() for c in chunks if c.strip()]
