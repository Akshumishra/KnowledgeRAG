# Azure Deployment Guide — KnowledgeAI Platform (Docker)

## Architecture Overview

```
  Browser
     │
     ▼
Azure App Service (Docker container)
  ├── FastAPI backend  (serves /api/*)
  ├── Static frontend  (serves /  → HTML/JS/CSS)
  └── Connects to:
        ├── Azure Database for PostgreSQL (Flexible Server)
        └── Azure Blob Storage (document uploads)
```

---

## Prerequisites

Install these tools on your machine:
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) — `az`
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A free or paid **Azure subscription**

---

## Step 1 — Log In to Azure

```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_NAME_OR_ID"
```

---

## Step 2 — Create a Resource Group

```bash
az group create --name knowledgeai-rg --location eastus
```

> Pick a region close to your users: `eastus`, `westeurope`, `southeastasia`, etc.

---

## Step 3 — Create Azure Container Registry (ACR)

```bash
az acr create \
  --resource-group knowledgeai-rg \
  --name knowledgeairegistry \
  --sku Basic \
  --admin-enabled true
```

Get your registry credentials:
```bash
az acr credential show --name knowledgeairegistry
```
Note the `username` and one of the `passwords`.

---

## Step 4 — Build & Push the Docker Image

```bash
# Log Docker into ACR
az acr login --name knowledgeairegistry

# Build (run from the repo root where Dockerfile lives)
docker build -t knowledgeai:latest .

# Tag for ACR
docker tag knowledgeai:latest knowledgeairegistry.azurecr.io/knowledgeai:latest

# Push
docker push knowledgeairegistry.azurecr.io/knowledgeai:latest
```

---

## Step 5 — Create Azure Database for PostgreSQL (Flexible Server)

```bash
az postgres flexible-server create \
  --resource-group knowledgeai-rg \
  --name knowledgeai-db \
  --location eastus \
  --admin-user dbadmin \
  --admin-password "StrongPassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --public-access 0.0.0.0
```

Enable the `pgvector` extension:
```bash
az postgres flexible-server parameter set \
  --resource-group knowledgeai-rg \
  --server-name knowledgeai-db \
  --name azure.extensions \
  --value vector
```

Create the database:
```bash
az postgres flexible-server db create \
  --resource-group knowledgeai-rg \
  --server-name knowledgeai-db \
  --database-name ragdb
```

Your `DATABASE_URL` will be:
```
postgresql+psycopg://dbadmin:StrongPassword123!@knowledgeai-db.postgres.database.azure.com:5432/ragdb
```

---

## Step 6 — Create Azure App Service Plan & Web App

```bash
# Create an App Service Plan (B2 = 2 vCPU, 3.5 GB RAM, ~$55/month)
az appservice plan create \
  --resource-group knowledgeai-rg \
  --name knowledgeai-plan \
  --is-linux \
  --sku B2

# Create the Web App pointing to your ACR image
az webapp create \
  --resource-group knowledgeai-rg \
  --plan knowledgeai-plan \
  --name knowledgeai-app \
  --deployment-container-image-name knowledgeairegistry.azurecr.io/knowledgeai:latest

# Allow App Service to pull from ACR
az webapp config container set \
  --resource-group knowledgeai-rg \
  --name knowledgeai-app \
  --docker-registry-server-url https://knowledgeairegistry.azurecr.io \
  --docker-registry-server-user knowledgeairegistry \
  --docker-registry-server-password "YOUR_ACR_PASSWORD"
```

---

## Step 7 — Set Environment Variables

Replace the values below with your real secrets:

```bash
az webapp config appsettings set \
  --resource-group knowledgeai-rg \
  --name knowledgeai-app \
  --settings \
    DATABASE_URL="postgresql+psycopg://dbadmin:StrongPassword123!@knowledgeai-db.postgres.database.azure.com:5432/ragdb" \
    SECRET_KEY="GENERATE_A_LONG_RANDOM_KEY_HERE" \
    ENCRYPTION_KEY="YOUR_FERNET_KEY_HERE" \
    JWT_ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="60" \
    REFRESH_TOKEN_EXPIRE_DAYS="7" \
    APP_ENV="production" \
    WEBSITES_PORT="8000"
```

> **Generate a Fernet key:** Run `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` locally.

---

## Step 8 — Run Database Migrations

After the container starts, run migrations via the App Service console:

```bash
# Open the App Service SSH console
az webapp ssh --resource-group knowledgeai-rg --name knowledgeai-app

# Inside the container
cd /app/backend
python -c "
import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from src.api.main import app
print('App loaded — DB tables created by lifespan.')
"
```

Or use `alembic` if you have migrations set up:
```bash
alembic upgrade head
```

---

## Step 9 — Verify Deployment

```bash
az webapp show \
  --resource-group knowledgeai-rg \
  --name knowledgeai-app \
  --query defaultHostName \
  --output tsv
```

Visit: `https://knowledgeai-app.azurewebsites.net`

---

## Step 10 — Auto-Deploy on Push (Optional CI/CD)

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Build & Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to ACR
        uses: docker/login-action@v3
        with:
          registry: knowledgeairegistry.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Build & Push
        run: |
          docker build -t knowledgeairegistry.azurecr.io/knowledgeai:latest .
          docker push knowledgeairegistry.azurecr.io/knowledgeai:latest

      - name: Deploy to Azure App Service
        uses: azure/webapps-deploy@v3
        with:
          app-name: knowledgeai-app
          publish-profile: ${{ secrets.AZURE_PUBLISH_PROFILE }}
          images: knowledgeairegistry.azurecr.io/knowledgeai:latest
```

Add these GitHub secrets:
- `ACR_USERNAME` / `ACR_PASSWORD` — from Step 3
- `AZURE_PUBLISH_PROFILE` — download from App Service → "Get publish profile"

---

## Estimated Monthly Cost

| Service | Tier | ~Cost/month |
|---|---|---|
| App Service | B2 Linux | ~$55 |
| PostgreSQL Flexible | B1ms (1 vCPU) | ~$15 |
| Container Registry | Basic | ~$5 |
| Blob Storage | LRS 50 GB | ~$1 |
| **Total** | | **~$76/month** |

> Scale down to B1 App Service (~$14/month) for dev/testing.

---

> [!TIP]
> Enable **Azure CDN** in front of your App Service to cache static frontend assets (HTML, JS, CSS) and dramatically reduce latency.

> [!IMPORTANT]
> Never put secrets in the `Dockerfile` or commit `.env` to git. Always use **App Service → Configuration → Application settings**.
