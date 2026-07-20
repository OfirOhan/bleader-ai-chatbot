# AutoSage — a grounded car-advice chatbot

A proof-of-concept AI chatbot that helps people understand and compare cars using
real automotive road-test content. It ingests eight professional reviews from
[auto.co.il](https://www.auto.co.il), builds a searchable vector knowledge base,
and holds a natural conversation whose answers are **grounded in the retrieved
reviews** (not hallucinated) — while gradually inferring what the user is looking
for.

Built for the AI Chatbot take-home assignment.

---

## What it does

- **Ingests & understands** the 8 road-test articles (Hebrew, real-world unstructured text).
- **Retrieves** the most relevant passages for each question using vector search over a local **ChromaDB**.
- **Answers** conversationally, grounded strictly in the retrieved passages, with **source citations** back to the original articles.
- **Infers preferences** as you chat (budget, body type, powertrain, priorities, shortlist) and shows them live.
- **Replies in your language** — ask in Hebrew or English.
- Wraps it all in a polished **web chat UI** (React) with light/dark themes and RTL support.

---

## Architecture

```
              ┌──────────── ingest (one-off) ─────────────┐
  auto.co.il  │  fetch → extract main text (trafilatura)  │
  8 articles ─┼─→ chunk (≈900 chars, overlapped)          │
              │  → translate he→en (Gemini, cached)       │
              │  → embed en (all-MiniLM-L6-v2)            │
              │  → store {Hebrew doc + vector + car,url}   │→  ChromaDB (local, persistent)
              └───────────────────────────────────────────┘

  ┌──────────────────────── chat turn ────────────────────────┐
  │  user question                                             │
  │    → translate he→en → embed → ChromaDB top-k retrieval    │
  │    → update inferred preference profile (Gemini, JSON)     │
  │    → build grounded prompt (history + prefs + passages)    │
  │    → Gemini answer in the user's language + citations      │
  └────────────────────────────────────────────────────────────┘

  React UI  ──HTTP──▶  FastAPI  ──▶  rag.py ──▶ {ChromaDB, MiniLM, Gemini}
                          └──▶ SQLite (users, conversations, messages)
```

### Components

| Layer | Choice | Why |
|-------|--------|-----|
| Vector DB | **ChromaDB** (local, persistent) | Assignment requirement; zero-setup, runs in-process. |
| Embeddings | **`sentence-transformers/all-MiniLM-L6-v2`** | Assignment option B — local, free, no API key. |
| LLM | **Gemini** (`google-genai`) | Generation, Hebrew↔English translation, preference extraction. |
| Extraction | **trafilatura** (+ BeautifulSoup fallback) | Robustly isolates article body from nav/ads/comments. |
| API | **FastAPI** + **SQLite** | Small, synchronous, dependency-light. |
| UI | **React + Vite** | Reused/rebranded from an existing chat app of mine. |

### Key design decision — the Hebrew ↔ MiniLM trade-off

The articles are in **Hebrew**, but `all-MiniLM-L6-v2` is trained on **English**
and retrieves Hebrew poorly. Rather than switch models (the two allowed options
were MiniLM or Azure `text-embedding-3-small`), I keep MiniLM and **translate to
English at ingest time**: each chunk is translated once (cached to disk), the
**English** text is embedded, and the **original Hebrew** is stored as the
document and used for grounding — so the answer never round-trips through a lossy
translation. User questions are translated the same way before retrieval, so the
query lands in the same monolingual English vector space. This keeps retrieval
quality high while honoring the model constraint.

### Grounding & anti-hallucination

The system prompt restricts the model to the retrieved passages, tells it to say
so when something isn't covered, and forbids inventing specs/prices. Every answer
returns the set of source cars/URLs it drew from, rendered as clickable citation
chips in the UI.

### Gradual preference inference

After each user turn a small JSON-mode Gemini call updates a running preference
profile (`budget`, `body_type`, `powertrain`, `usage`, `priorities`,
`candidates`). The profile is (a) persisted on the conversation, (b) fed back into
the answer prompt so advice gets more personal over time, and (c) shown to the
user as a live "What I know so far" bar.

---

## Project layout

```
autosage/
├── backend/
│   ├── config.py       # env + paths
│   ├── corpus.py       # the 8 articles; fetch / extract / chunk
│   ├── translate.py    # he→en with a persistent cache
│   ├── embeddings.py   # MiniLM wrapper
│   ├── store.py        # ChromaDB access
│   ├── ingest.py       # build the knowledge base  (python -m backend.ingest)
│   ├── llm.py          # Gemini client (text + JSON + translation)
│   ├── rag.py          # retrieve → infer prefs → grounded answer
│   ├── db.py           # SQLite (users, conversations, messages)
│   └── app.py          # FastAPI endpoints
├── frontend/           # React + Vite chat UI
├── docs/EXAMPLE.md     # a sample interaction
├── pyproject.toml      # deps + project metadata (uv)
├── uv.lock             # pinned, reproducible dependency versions
└── .env.example
```

---

## Quickstart

**Prereqs:** [uv](https://docs.astral.sh/uv/), Node 18+, and a Gemini API key
([aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
uv installs Python 3.10+ for you if you don't have it.

```bash
# 1. Backend deps + key
uv sync                         # creates .venv and installs from the lockfile
cp .env.example .env            # then paste your GEMINI_API_KEY into .env

# 2. Build the knowledge base (fetches the 8 articles, ~1–2 min the first time)
uv run python -m backend.ingest

# 3. Run the API (http://127.0.0.1:8000)
uv run uvicorn backend.app:app --reload

# 4. Run the UI (separate terminal → http://localhost:5173)
cd frontend
npm install
npm run dev
```

> `uv run <cmd>` runs a command inside the project environment (no manual
> `activate` needed). Prefer it over `pip`/`python` directly.

Open http://localhost:5173, sign in with any email, and start asking about cars.

> `python -m backend.ingest` is required once before chatting — it populates
> ChromaDB. Re-run with `--refresh` to re-download the articles.

---

## Notes, scope & trade-offs

- **Scope:** this is a POC, not production. Auth is "email = credential" (no
  password) so the demo has per-user history without friction. Ingest and chat
  are synchronous.
- **Cost/perf:** translation is cached, so ingest only pays for it once;
  retrieval + one answer call is the steady-state cost per message.
- **The 8 cars:** Citroën C3 (2026), Audi RS3 (facelift), Kia EV9 (long-term),
  MG S6, Hyundai Elantra N (manual), Aion HT, Lynk & Co 01 (2026), Genesis GV80 (2026).
- **What I'd add next:** streaming responses, showing the exact quoted sentence
  per citation, a cross-encoder re-rank step, and evaluation on a small Q&A set.

See **[docs/EXAMPLE.md](docs/EXAMPLE.md)** for a sample conversation.
