from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """
    Generic Base Repository to handle basic CRUD operations for SQLAlchemy models.
    Automatically filters out soft-deleted records if the model has a deleted_at column.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by(self, **kwargs) -> ModelType | None:
        stmt = select(self.model).filter_by(**kwargs)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self, *, skip: int = 0, limit: int = 100, **kwargs
    ) -> list[ModelType]:
        stmt = select(self.model).filter_by(**kwargs)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        return obj

    async def soft_delete(self, id: Any) -> bool:
        """Soft delete a record by setting deleted_at to current UTC time."""
        if not hasattr(self.model, "deleted_at"):
            raise ValueError(
                f"Model {self.model.__name__} does not support soft delete"
            )
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, id: Any) -> bool:
        """Hard delete a record from the database."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
