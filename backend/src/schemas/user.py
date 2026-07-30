from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    workspace_id: str | None = None
    email: str
    full_name: str
    role: str | None = None
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserActivityRequest(BaseModel):
    last_route: str
    last_conversation_id: str | None = None


class UserActivityResponse(BaseModel):
    last_route: str
    last_conversation_id: str | None = None

    model_config = {"from_attributes": True}
