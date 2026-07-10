from typing import Optional
from sqlalchemy import Boolean, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import BaseModel


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    join_code: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )

    members = relationship(
        "User",
        secondary="workspace_members",
        back_populates="workspaces",
        viewonly=True,
    )


class WorkspaceAPIKey(BaseModel):
    __tablename__ = "organization_api_keys"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[str] = mapped_column(String(50))
    encrypted_key: Mapped[str] = mapped_column(String(1024))
    key_preview: Mapped[str] = mapped_column(String(20))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkspaceModel(BaseModel):
    __tablename__ = "organization_models"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
