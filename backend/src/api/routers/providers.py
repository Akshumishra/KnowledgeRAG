from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from src.schemas.provider import (
    ProviderResponse,
    APIKeyCreate,
    ProviderToggleRequest,
    ProviderCreate,
)
from src.services.provider_service import ProviderService
from src.api.dependencies import get_service, get_current_user
from src.models.auth import User

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=List[ProviderResponse])
async def list_providers(
    service: ProviderService = Depends(get_service(ProviderService)),
):
    return await service.list_providers()


@router.post("", response_model=ProviderResponse)
async def create_provider(
    data: ProviderCreate,
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    """Owner-only: add a new custom provider globally."""
    return await service.create_provider(data, current_user.workspace_id, current_user)


@router.get("/active")
async def list_active_providers(
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    return await service.get_active_providers(current_user.workspace_id)


@router.get("/workspace-models")
async def get_workspace_models(
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    """Return {provider_id: [model_name, ...]} for the current workspace."""
    return await service.get_workspace_models(current_user.workspace_id)


@router.get("/keys")
async def get_org_keys(
    scope: str = "user",
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    return await service.get_api_keys(current_user.workspace_id, current_user, scope)


@router.post("/keys")
async def add_api_key(
    data: APIKeyCreate,
    scope: str = "user",
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    return await service.add_api_key(
        current_user.workspace_id, data, current_user, scope
    )


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: str,
    scope: str = "user",
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    await service.delete_api_key(key_id, current_user.workspace_id, current_user, scope)
    return {"status": "deleted"}


@router.patch("/keys/{key_id}")
async def toggle_api_key(
    key_id: str,
    data: ProviderToggleRequest,
    scope: str = "user",
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    await service.toggle_api_key(
        key_id, current_user.workspace_id, current_user, scope, data.is_enabled
    )
    return {"status": "success", "is_enabled": data.is_enabled}


@router.get("/{provider_id}/health")
async def check_provider_health(
    provider_id: str,
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    try:
        is_healthy = await service.check_health(
            provider_id, current_user.workspace_id, current_user
        )
        return {"healthy": is_healthy}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


@router.get("/{provider_id}/models")
async def list_provider_models(
    provider_id: str,
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    try:
        models = await service.list_models(
            provider_id, current_user.workspace_id, current_user
        )
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


class SaveModelsRequest(BaseModel):
    models: List[str]


@router.post("/{provider_id}/models")
async def save_provider_models(
    provider_id: str,
    data: SaveModelsRequest,
    service: ProviderService = Depends(get_service(ProviderService)),
    current_user: User = Depends(get_current_user),
):
    """Owner-only: Save the allowed model list for a provider in this workspace."""
    await service.save_workspace_models(
        current_user.workspace_id, provider_id, data.models, current_user
    )
    return {"status": "saved", "provider_id": provider_id, "models": data.models}
