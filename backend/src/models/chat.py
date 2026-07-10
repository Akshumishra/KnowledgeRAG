from datetime import datetime
from typing import Optional
from sqlalchemy import Float, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import BaseModel


class Conversation(BaseModel):
    __tablename__ = "conversations"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(20), default="completed"
    )  # 'thinking', 'generating', 'completed', 'failed'
    generation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sources_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array
