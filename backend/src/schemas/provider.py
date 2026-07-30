from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str
    slug: str
    default_models: str | None = ""
    is_local: bool = False


class APIKeyCreate(BaseModel):
    provider_id: str
    api_key: str = Field(..., min_length=1)
    display_name: str | None = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    slug: str
    default_models: str | None = None


class SaveModelsRequest(BaseModel):
    models: list[str]
    api_key_id: str


class ProviderToggleRequest(BaseModel):
    is_enabled: bool


class ModelInfo(BaseModel):
    provider: str
    model_id: str
    name: str
    context_window: int = 0
