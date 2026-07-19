"""FastAPI server.

Implements exactly the endpoints the React frontend calls:
  auth (email), conversations CRUD, messages (POST runs the RAG turn).
Auth is a simple email-is-the-credential bearer scheme — fine for a POC, and it
lets the polished sign-in screen work unchanged.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, rag, schemas, store

app = FastAPI(title="AutoSage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # POC: any origin (the Vite dev server proxies anyway)
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth helper -------------------------------------------------------------

def current_user(authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    user = db.user_for_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# --- Health / auth -----------------------------------------------------------

@app.get("/api/health")
def health():
    try:
        n = store.count()
    except Exception:
        n = 0
    return {"status": "ok", "indexed_chunks": n}


@app.get("/api/auth/config")
def auth_config():
    return {}  # Google sign-in not configured; the UI hides it.


@app.post("/api/auth/email")
def auth_email(body: schemas.EmailAuthIn):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    user = db.get_or_create_user(email)
    token = db.issue_token(user["id"])
    return {"token": token, "user": user}


# --- Conversations -----------------------------------------------------------

@app.post("/api/conversations")
def create_conversation(body: schemas.ConversationIn, user=Depends(current_user)):
    return db.create_conversation(user["id"], body.title)


@app.get("/api/conversations")
def list_conversations(user=Depends(current_user)):
    return db.list_conversations(user["id"])


@app.delete("/api/conversations/{cid}")
def delete_conversation(cid: str, user=Depends(current_user)):
    db.delete_conversation(cid, user["id"])
    return {"ok": True}


# --- Messages ----------------------------------------------------------------

@app.get("/api/conversations/{cid}/messages")
def get_messages(cid: str, user=Depends(current_user)):
    if not db.get_conversation(cid, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return db.list_messages(cid)


@app.post("/api/conversations/{cid}/messages")
def post_message(cid: str, body: schemas.MessageIn, user=Depends(current_user)):
    conv = db.get_conversation(cid, user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Empty message")

    # Persist the user's turn, then run RAG over the prior history.
    history = db.history_for(cid)
    user_msg = db.add_message(cid, "user", content)

    try:
        result = rag.answer(content, history, conv.get("preferences", {}))
    except Exception as exc:  # noqa: BLE001
        # Surface a friendly assistant message instead of a 500 so the chat UI
        # stays usable even if the model/key is misconfigured.
        result = {
            "content": f"Sorry — I couldn't generate an answer ({exc}).",
            "sources": [],
            "preferences": conv.get("preferences", {}),
        }

    assistant_msg = db.add_message(cid, "assistant", result["content"], result["sources"])

    # Title the conversation from the first question; persist inferred prefs.
    title = conv.get("title") or content[:60]
    db.update_conversation(cid, title=title, preferences=result["preferences"])

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "preferences": result["preferences"],
        "conversation_title": title,
    }
