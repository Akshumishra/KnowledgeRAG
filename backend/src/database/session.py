from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.core.config import settings


@lru_cache(maxsize=1)
def _get_engine():
    """
    Lazily create the SQLAlchemy async engine.

    Deferring creation to call-time (rather than module import time) means:
    - Tests can set DATABASE_URL before anything is instantiated.
    - The engine is still a singleton for the process lifetime.
    """
    _is_sqlite = settings.database_url.startswith("sqlite")
    pool_kwargs = (
        {}
        if _is_sqlite
        else {"pool_size": 10, "max_overflow": 20}
    )
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_pre_ping=not _is_sqlite,
        **pool_kwargs,
    )


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=_get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def AsyncSessionLocal() -> AsyncSession:
    """
    Returns a new AsyncSession from the lazily-initialised session factory.

    Calling convention is identical to the previous module-level
    ``async_sessionmaker`` instance, so all existing callers (UnitOfWork,
    get_db, etc.) work without change.
    """
    return _get_session_factory()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    Usually you don't use this directly in services if you use UnitOfWork.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
