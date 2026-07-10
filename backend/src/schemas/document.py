from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str]
    is_enabled: bool = True
    chunk_count: int
    version: int
    created_by: Optional[str]
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentToggleRequest(BaseModel):
    is_enabled: bool
