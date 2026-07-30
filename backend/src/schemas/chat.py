from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(..., max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    status: str = "completed"
    created_at: datetime
    sources: list[dict[str, Any]] = []
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    model_id: str | None = None
    latency_ms: float | None = None

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
