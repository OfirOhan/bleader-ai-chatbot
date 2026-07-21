#!/bin/sh
# One-command startup: build the knowledge base on first run, then serve.
# Idempotent — if the volume already holds an ingested KB, ingest is skipped,
# so `docker compose up` is cheap on every boot after the first.
set -e

COUNT=$(python -c "from backend import store; print(store.count())" 2>/dev/null || echo 0)

if [ "$COUNT" = "0" ]; then
  if [ -n "$GEMINI_API_KEY" ]; then
    echo "[entrypoint] Knowledge base empty — running one-time ingest..."
    python -m backend.ingest || echo "[entrypoint] ingest failed; starting API anyway"
  else
    echo "[entrypoint] No GEMINI_API_KEY set and KB empty — starting API without ingest."
  fi
else
  echo "[entrypoint] Knowledge base ready ($COUNT chunks) — skipping ingest."
fi

exec "$@"
