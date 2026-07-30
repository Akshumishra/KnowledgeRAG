from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.schemas.conversation import RetrievedSource


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_id: str | None = None
    latency_ms: float
    retrieved_sources: list[RetrievedSource] = []
    feedback: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageFeedback(BaseModel):
    feedback: str
