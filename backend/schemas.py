"""Request/response models for the API."""
from __future__ import annotations

from pydantic import BaseModel


class EmailAuthIn(BaseModel):
    email: str


class ConversationIn(BaseModel):
    title: str | None = None


class MessageIn(BaseModel):
    content: str
    lang: str = "en"
