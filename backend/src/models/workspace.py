
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    join_code: Mapped[str | None] = mapped_column(
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
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_providers.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    encrypted_key: Mapped[str] = mapped_column(String(1024))
    key_preview: Mapped[str] = mapped_column(String(20))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkspaceModel(BaseModel):
    __tablename__ = "organization_models"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_providers.id", ondelete="CASCADE"), index=True
    )
    api_key_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organization_api_keys.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
