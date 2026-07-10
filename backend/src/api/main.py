from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.database.session import engine
from src.models.base import Base
from src.core.config import settings
from src.core.logging import setup_logging
from sqlalchemy import select, text, update
from src.models.settings import LLMProvider
from src.core.constants import DefaultLLMProviders
from datetime import datetime, timedelta, timezone
from src.models.chat import Message
from src.api.routers import (
    auth,
    documents,
    conversations,
    chat,
    providers,
    users,
    analytics,
)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Enterprise AI Knowledge Platform...")
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.upload_dir)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created.")
        result = await conn.execute(select(LLMProvider).limit(1))
        if not result.first():
            providers = [LLMProvider(**p) for p in DefaultLLMProviders.PROVIDERS]

            async with AsyncSession(conn) as session:
                session.add_all(providers)
                await session.commit()
            logger.info("Seeded default LLM providers.")

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stmt = (
            update(Message)
            .where(
                Message.status.in_(["thinking", "generating"]),
                Message.started_at < cutoff,
            )
            .values(
                status="failed",
                error_message="Generation timed out or server restarted",
                completed_at=datetime.now(timezone.utc),
            )
        )
        await conn.execute(stmt)
        logger.info("Recovered stuck messages (if any).")

    yield

    logger.info("Shutting down Enterprise AI Knowledge Platform")


app = FastAPI(
    title="Enterprise AI Knowledge Platform",
    description="Multi-tenant RAG platform with streaming chat, RBAC, and multi-provider LLM support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

_static_dir = Path(__file__).parent.parent.parent.parent / "frontend"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/api/v1/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa(full_path: str = ""):
    """Serve the frontend SPA for all non-API routes."""
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    index = _static_dir / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>Frontend not built yet</h1>", status_code=503)
    return FileResponse(str(index))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )
