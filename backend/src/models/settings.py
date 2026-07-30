
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class LLMProvider(BaseModel):
    __tablename__ = "llm_providers"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    default_models: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelCapability(BaseModel):
    __tablename__ = "model_capabilities"

    provider_id: Mapped[str] = mapped_column(String(36), index=True)
    model_name: Mapped[str] = mapped_column(String(100), index=True)
    capability_state: Mapped[str] = mapped_column(String(50), default="Unknown")
    last_verified: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
