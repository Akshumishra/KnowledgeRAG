# ── KnowledgeAI Platform — Dockerfile ─────────────────────────────────
# Multi-stage build: install deps separately to keep final image lean.

# ── Stage 1: Dependency installer ─────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /install

# System libraries needed by psycopg, sentence-transformers, docling, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev build-essential curl git \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast pip alternative)
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
# Install all dependencies into the system Python
RUN uv pip install --system --no-cache .

# ── Stage 2: Final runtime image ───────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Only runtime libs needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Directory for uploads (override via volume / Azure Storage in production)
RUN mkdir -p /app/uploads /app/logs

# Startup script: run DB migrations then start the server
RUN printf '#!/bin/sh\nset -e\necho "Checking DB initialization..."\ncd /app/backend\npython -m src.database.stamp_db\necho "Running DB migrations..."\nalembic upgrade head\necho "Starting server..."\nexec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2\n' > /app/start.sh && chmod +x /app/start.sh

# Port to expose
EXPOSE 8000

# Health check (Azure App Service uses this)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Working dir for the app process (uvicorn runs from here)
WORKDIR /app/backend

CMD ["/app/start.sh"]
