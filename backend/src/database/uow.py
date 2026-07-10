from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import AsyncSessionLocal


class UnitOfWork:
    """
    Manages database transactions securely. Services use UoW instead of AsyncSession.
    """

    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        if self.session:
            await self.session.commit()

    async def rollback(self):
        if self.session:
            await self.session.rollback()

    async def flush(self):
        if self.session:
            await self.session.flush()
