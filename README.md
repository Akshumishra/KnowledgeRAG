# KnowledgeRAG: Enterprise AI Knowledge Platform

**KnowledgeRAG** is an enterprise-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform designed to help teams organize, query, and interact with their internal data securely. 

Built with a lightning-fast FastAPI/PostgreSQL backend and a sleek, zero-dependency Vanilla JS frontend, it utilizes vector embeddings (`pgvector`) to provide highly accurate, context-aware AI interactions.

## Key Features

- **Multi-Tenant Workspaces**: Completely isolate data, users, and conversations by team or organization.
- **Robust Security & Auth**: OTP email verification, secure JWT session management, and granular Role-Based Access Control (RBAC) separating Workspace Owners and standard Members.
- **Smart Document Processing**: Upload, chunk, and intelligently embed documents into a vector database for ultra-fast semantic search.
- **LLM Agnostic**: Seamlessly plug in external providers (like OpenAI, Google Gemini, Groq, OpenRouter) or run 100% locally with Ollama models.
- **Real-time Streaming Chat**: Token-by-token streaming responses for a snappy, ChatGPT-like user experience.
- **Azure Ready**: Fully containerized with automated PowerShell scripts for effortless deployment to Azure App Service and PostgreSQL Flexible Server.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0 (Async)
- **Database**: PostgreSQL with `pgvector` extension
- **Frontend**: Vanilla JavaScript (ES Modules), Vanilla CSS
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

## Local Installation & Setup

1. **Clone the repository and install dependencies**
   We use `uv` for lightning-fast dependency management:
   ```powershell
   git clone https://github.com/Akshumishra/KnowledgeRAG1.git
   cd KnowledgeRAG1
   uv sync
   ```

2. **Environment Configuration**
   Create a `.env` file in the root directory and configure your secrets:
   ```env
   # Application
   APP_ENV=development
   SECRET_KEY=your-super-secret-key
   ENCRYPTION_KEY=your-fernet-encryption-key
   
   # Database (Ensure pgvector is installed)
   DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/knowledge_platform
   
   # SMTP for Email Verification
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=your_smtp_user
   SMTP_PASSWORD=your_smtp_password
   SMTP_FROM_EMAIL=your_email@gmail.com
   SMTP_USE_TLS=true
   
   # LLM Providers (Configure the ones you want to use)
   OPENAI_API_KEY=sk-...
   GOOGLE_API_KEY=AIza...
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **Start the Application**
   Run the provided startup script to launch the FastAPI server and initialize database migrations:
   ```powershell
   ./start.ps1
   ```
   The application will be available at `http://localhost:8000`.

## Azure Deployment

This repository includes fully automated deployment to Microsoft Azure.

1. **First-time Deployment**: 
   Run `.\Deployment_Scripts\deploy_to_azure.ps1`. 
   The script will interactively ask for your API keys and SMTP credentials, provision a Resource Group, Azure Container Registry, PostgreSQL Flexible Server, and an App Service, and securely inject your configuration.

2. **Deploying Updates**:
   Updates are completely automated via **GitHub Actions CI/CD**.
   When you make changes to the code, simply commit and push your changes to the `main` branch. The CI/CD pipeline (`.github/workflows/ci-cd.yml`) will automatically build the new Docker image, run tests, and push the latest version to your live Azure App Service environment.
