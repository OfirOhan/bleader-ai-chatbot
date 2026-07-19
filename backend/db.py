"""Minimal SQLite persistence (stdlib only — no ORM needed for a POC).

Tables: users, tokens (bearer auth), conversations (with an inferred-preference
profile), and messages (assistant messages carry their source citations).
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
import uuid
from typing import Any

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _now() -> float:
    return time.time()


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                display_name TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                preferences TEXT,
                created_at REAL,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                sources TEXT,
                created_at REAL
            );
            """
        )
        _conn.commit()
    return _conn


def _id() -> str:
    return uuid.uuid4().hex


# --- Users / auth ------------------------------------------------------------

def get_or_create_user(email: str) -> dict:
    with _lock:
        db = _db()
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            uid = _id()
            display = email.split("@")[0]
            db.execute(
                "INSERT INTO users (id, email, display_name, created_at) VALUES (?,?,?,?)",
                (uid, email, display, _now()),
            )
            db.commit()
            row = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return _user_dict(row)


def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        db = _db()
        db.execute("INSERT INTO tokens (token, user_id) VALUES (?,?)", (token, user_id))
        db.commit()
    return token


def user_for_token(token: str) -> dict | None:
    with _lock:
        db = _db()
        row = db.execute(
            "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
            (token,),
        ).fetchone()
        return _user_dict(row) if row else None


def _user_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "onboarded": True,   # AutoSage skips onboarding
        "plan": "free",
    }


# --- Conversations -----------------------------------------------------------

def create_conversation(user_id: str, title: str | None) -> dict:
    with _lock:
        db = _db()
        cid = _id()
        now = _now()
        db.execute(
            "INSERT INTO conversations (id,user_id,title,preferences,created_at,updated_at)"
            " VALUES (?,?,?,?,?,?)",
            (cid, user_id, title, json.dumps({}), now, now),
        )
        db.commit()
        return _conv_dict(db.execute(
            "SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone())


def list_conversations(user_id: str) -> list[dict]:
    with _lock:
        db = _db()
        rows = db.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [_conv_dict(r) for r in rows]


def get_conversation(cid: str, user_id: str) -> dict | None:
    with _lock:
        db = _db()
        row = db.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (cid, user_id)
        ).fetchone()
        return _conv_dict(row) if row else None


def delete_conversation(cid: str, user_id: str) -> None:
    with _lock:
        db = _db()
        db.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (cid, user_id))
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
        db.commit()


def update_conversation(cid: str, *, title: str | None = None,
                        preferences: dict | None = None) -> None:
    with _lock:
        db = _db()
        if title is not None:
            db.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, cid))
        if preferences is not None:
            db.execute("UPDATE conversations SET preferences = ? WHERE id = ?",
                       (json.dumps(preferences, ensure_ascii=False), cid))
        db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), cid))
        db.commit()


def get_preferences(cid: str) -> dict:
    with _lock:
        db = _db()
        row = db.execute("SELECT preferences FROM conversations WHERE id = ?", (cid,)).fetchone()
        if not row or not row["preferences"]:
            return {}
        try:
            return json.loads(row["preferences"])
        except json.JSONDecodeError:
            return {}


def _conv_dict(row: sqlite3.Row) -> dict:
    prefs = {}
    try:
        prefs = json.loads(row["preferences"]) if row["preferences"] else {}
    except json.JSONDecodeError:
        prefs = {}
    return {
        "id": row["id"],
        "title": row["title"],
        "preferences": prefs,
        "created_at": row["created_at"],
    }


# --- Messages ----------------------------------------------------------------

def add_message(conversation_id: str, role: str, content: str,
                sources: list[dict] | None = None) -> dict:
    with _lock:
        db = _db()
        mid = _id()
        now = _now()
        db.execute(
            "INSERT INTO messages (id,conversation_id,role,content,sources,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (mid, conversation_id, role, content,
             json.dumps(sources or [], ensure_ascii=False), now),
        )
        db.commit()
        return db_message(mid)


def db_message(mid: str) -> dict:
    db = _db()
    row = db.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
    return _msg_dict(row)


def list_messages(conversation_id: str) -> list[dict]:
    with _lock:
        db = _db()
        rows = db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return [_msg_dict(r) for r in rows]


def history_for(conversation_id: str) -> list[dict]:
    """Chronological [{role, content}] for feeding back into the model."""
    return [{"role": m["role"], "content": m["content"]}
            for m in list_messages(conversation_id)]


def _msg_dict(row: sqlite3.Row) -> dict[str, Any]:
    try:
        sources = json.loads(row["sources"]) if row["sources"] else []
    except json.JSONDecodeError:
        sources = []
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "sources": sources,
        "status": "ready",
        "created_at": row["created_at"],
    }
