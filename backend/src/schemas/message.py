from __future__ import annotations

from datetime import datetime
from typing import List, Optional
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
    model_id: Optional[str] = None
    latency_ms: float
    retrieved_sources: List[RetrievedSource] = []
    feedback: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageFeedback(BaseModel):
    feedback: str
