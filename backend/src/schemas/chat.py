from datetime import datetime
from typing import Optional, List, Dict, Any
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
    sources: List[Dict[str, Any]] = []
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_id: Optional[str] = None
    latency_ms: Optional[float] = None

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
