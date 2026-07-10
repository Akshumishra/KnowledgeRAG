# Enterprise AI Knowledge Platform

An enterprise-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform. Built with FastAPI, this application provides role-based access control (RBAC), streaming chat interfaces, and multi-provider LLM support.

## Features

- **Multi-Tenant Architecture**: Isolate data and conversations by workspace/organization.
- **Advanced RAG**: Document uploading, chunking, and vector search.
- **Multi-Provider LLM Integration**: Support for OpenAI, Google Gemini, Groq, OpenRouter, and local Ollama models.
- **Streaming Chat**: Real-time token streaming for a responsive user experience.
- **Role-Based Access Control (RBAC)**: Secure access management for administrators and regular users.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)
- PostgreSQL with `pgvector` extension enabled

## Installation & Setup

1. **Clone the repository and install dependencies**
   We use `uv` for lightning-fast dependency management:
   ```powershell
   uv sync
   ```

2. **Environment Configuration**
   Create a `.env` file in the root directory (or copy from `.env.example` if available) and configure your secrets:
   ```env
   # Application
   APP_ENV=development
   SECRET_KEY=your-super-secret-key
   ENCRYPTION_KEY=your-fernet-encryption-key
   
   # Database
   DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/knowledge_platform
   
   # LLM Providers (Configure the ones you want to use)
   OPENAI_API_KEY=sk-...
   GOOGLE_API_KEY=AIza...
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **Start the Application**
   Run the provided startup script to launch the FastAPI server:
   ```powershell
   ./start.ps1
   ```
   
   *Note: If you encounter an "Access is denied" error during `uv sync` or startup, ensure no other terminals or IDE language servers (like Pylance) are locking the `.venv` directory.*

## Architecture

- **Backend**: FastAPI (Python) using asynchronous routing and SQLAlchemy 2.0.
- **Database**: PostgreSQL with `pgvector` for embeddings.
- **LLM Providers**: Abstraction layer seamlessly switching between OpenAI, Gemini, Groq, and Ollama.

## Troubleshooting

- **Gemini SDK Warning**: The backend has been migrated to use the latest `google-genai` SDK. Ensure you have run `uv sync` to apply this update and remove the deprecated `google-generativeai` package.
- **Missing Migrations**: If your database schema is outdated, ensure alembic migrations are run (usually handled automatically in `start.ps1` or run `alembic upgrade head`).

## License
Private and Confidential. All rights reserved.