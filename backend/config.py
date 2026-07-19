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
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"          # cached source HTML
CLEAN_DIR = DATA_DIR / "clean"      # extracted article text
CHROMA_DIR = DATA_DIR / "chroma"    # persistent vector store
TRANSLATION_CACHE = DATA_DIR / "translations.json"
DB_PATH = BACKEND_DIR / "autosage.db"

for _d in (DATA_DIR, RAW_DIR, CLEAN_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Models ------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()

# --- Retrieval ---------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "6"))
CHUNK_CHARS = 900          # target chunk size (characters)
CHUNK_OVERLAP = 150        # overlap between consecutive chunks
COLLECTION_NAME = "car_reviews"

# History turns fed back into the model as conversational context.
MAX_HISTORY_TURNS = 8
