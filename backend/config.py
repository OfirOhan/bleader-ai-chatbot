"""Central configuration — everything tunable in one place.

Values come from the environment (see .env.example). Paths are resolved
relative to this file so the app runs the same no matter the working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # read .env if present

# --- Paths -------------------------------------------------------------------
# DATA_DIR / DB_PATH honor env overrides so a container can point all mutable
# state (ChromaDB + SQLite) at a single mounted volume. Unset -> the original
# in-repo locations, so local dev is unchanged.
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = Path(os.getenv("AUTOSAGE_DATA_DIR") or BACKEND_DIR / "data")
RAW_DIR = DATA_DIR / "raw"          # cached source HTML
CLEAN_DIR = DATA_DIR / "clean"      # extracted article text
CHROMA_DIR = DATA_DIR / "chroma"    # persistent vector store
TRANSLATION_CACHE = DATA_DIR / "translations.json"
DB_PATH = Path(os.getenv("AUTOSAGE_DB_PATH") or BACKEND_DIR / "autosage.db")

for _d in (DATA_DIR, RAW_DIR, CLEAN_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Models ------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
RERANK_MODEL = os.getenv(
    "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
).strip()

# --- Retrieval ---------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "6"))            # chunks handed to the answer model
CANDIDATES = int(os.getenv("CANDIDATES", "20"))  # pool each retriever returns
RERANK_POOL = int(os.getenv("RERANK_POOL", "20"))  # fused pool sent to the reranker
RRF_K = 60                 # reciprocal-rank-fusion damping constant (standard default)
# Gate on the cross-encoder's top relevance score (an ms-marco logit: positive =
# relevant, negative = not). If the best reranked chunk falls below this, the
# answer model is told the reviews may not cover the question. This separates
# genuinely-covered questions (~+5) from off-topic ones (~-3) far better than
# cosine, which is fooled when a review merely *mentions* an outside car.
RELEVANCE_FLOOR = float(os.getenv("RELEVANCE_FLOOR", "0.0"))
CHUNK_CHARS = 900          # target chunk size (characters)
CHUNK_OVERLAP = 150        # overlap between consecutive chunks
COLLECTION_NAME = "car_reviews"

# History turns fed back into the model as conversational context.
MAX_HISTORY_TURNS = 8
