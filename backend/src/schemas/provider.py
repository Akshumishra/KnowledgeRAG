from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str
    slug: str
    default_models: Optional[str] = ""
    is_local: bool = False


class APIKeyCreate(BaseModel):
    provider_id: str
    api_key: str = Field(..., min_length=1)


class ProviderResponse(BaseModel):
    id: str
    name: str
    slug: str
    default_models: Optional[str] = None


class ProviderToggleRequest(BaseModel):
    is_enabled: bool


class ModelInfo(BaseModel):
    provider: str
    model_id: str
    name: str
    context_window: int = 0
