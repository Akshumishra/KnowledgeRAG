from typing import List, Dict, Any
from src.core.exceptions import NotFoundError, ForbiddenError
from src.core.crypto import encrypt, decrypt
from cryptography.fernet import InvalidToken
from src.database.uow import UnitOfWork
from src.database.repositories.workspace import WorkspaceAPIKeyRepository
from src.database.repositories.settings import (
    LLMProviderRepository,
    WorkspaceModelRepository,
)
from src.models.workspace import WorkspaceAPIKey, WorkspaceModel
from src.schemas.provider import APIKeyCreate, ProviderResponse
from sqlalchemy import select, delete
from src.models.settings import ModelCapability
from src.models.settings import LLMProvider
from src.models.auth import workspace_member_table
from src.providers.llm.factory import get_provider


class ProviderService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_providers(self) -> List[ProviderResponse]:
        async with self.uow:
            repo = LLMProviderRepository(self.uow.session)
            providers = await repo.list()
            return [
                ProviderResponse(
                    id=p.id,
                    name=p.name,
                    slug=p.slug,
                    default_models=p.default_models,
                )
                for p in providers
            ]

    async def create_provider(
        self, data: "ProviderCreate", workspace_id: str, actor: "User"
    ) -> ProviderResponse:
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError("Only owners can create LLM providers.")

        async with self.uow:
            new_provider = LLMProvider(
                name=data.name,
                slug=data.slug,
                default_models=data.default_models,
                is_local=data.is_local,
            )
            self.uow.session.add(new_provider)
            await self.uow.commit()
            return ProviderResponse(
                id=new_provider.id,
                name=new_provider.name,
                slug=new_provider.slug,
                default_models=new_provider.default_models,
            )

    async def get_active_providers(self, workspace_id: str) -> List[Dict[str, Any]]:
        async with self.uow:
            repo = WorkspaceAPIKeyRepository(self.uow.session)
            keys = await repo.list(workspace_id=workspace_id)
            return [
                {
                    "provider_id": k.provider_id,
                    "is_enabled": getattr(k, "is_enabled", True),
                    "health_status": "untested",
                }
                for k in keys
                if getattr(k, "is_enabled", True)
            ]

    async def _is_workspace_owner(self, user_id: str, workspace_id: str) -> bool:
        stmt = select(workspace_member_table.c.is_owner).where(
            workspace_member_table.c.user_id == user_id,
            workspace_member_table.c.workspace_id == workspace_id,
        )
        result = await self.uow.session.execute(stmt)
        return bool(result.scalar())

    async def get_api_keys(
        self, workspace_id: str, actor: "User", scope: str = "workspace"
    ) -> List[Dict[str, Any]]:
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError()

        async with self.uow:
            repo = WorkspaceAPIKeyRepository(self.uow.session)
            keys = await repo.list(workspace_id=workspace_id)

            result = []
            for k in keys:
                result.append(
                    {
                        "id": k.id,
                        "provider_id": k.provider_id,
                        "display_name": k.display_name,
                        "key_preview": k.key_preview,
                        "full_key": None,
                        "is_enabled": k.is_enabled,
                        "is_valid": k.is_valid,
                        "health_status": "untested",
                        "last_used_at": None,
                        "scope": scope,
                    }
                )
            return result

    async def add_api_key(
        self,
        workspace_id: str,
        data: APIKeyCreate,
        actor: "User",
        scope: str = "workspace",
    ) -> Dict[str, Any]:
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError()

        async with self.uow:
            encrypted_val = encrypt(data.api_key)
            preview = f"sk-...{data.api_key[-4:]}" if len(data.api_key) > 8 else "***"

            repo = WorkspaceAPIKeyRepository(self.uow.session)
            existing = await repo.get_by_org_and_provider(
                workspace_id, data.provider_id
            )
            if existing:
                existing.encrypted_key = encrypted_val
                existing.key_preview = preview
                existing.is_valid = True
                key_obj = existing
            else:
                key_obj = repo.add(
                    WorkspaceAPIKey(
                        workspace_id=workspace_id,
                        provider_id=data.provider_id,
                        display_name=data.display_name,
                        encrypted_key=encrypted_val,
                        key_preview=preview,
                        is_valid=True,
                    )
                )

            await self.uow.commit()

            return {
                "id": key_obj.id,
                "provider_id": key_obj.provider_id,
                "display_name": getattr(key_obj, "display_name", None),
                "key_preview": key_obj.key_preview,
                "full_key": None,
                "is_enabled": getattr(key_obj, "is_enabled", True),
                "health_status": "untested",
                "scope": scope,
            }

    async def delete_api_key(
        self, key_id: str, workspace_id: str, actor: "User", scope: str = "workspace"
    ) -> None:
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError()

        async with self.uow:
            repo = WorkspaceAPIKeyRepository(self.uow.session)
            key = await repo.get(key_id)
            if not key or key.workspace_id != workspace_id:
                raise NotFoundError("API Key", key_id)
            await repo.delete(key_id)
            await self.uow.commit()

    async def toggle_api_key(
        self,
        key_id: str,
        workspace_id: str,
        actor: "User",
        scope: str,
        is_enabled: bool,
    ) -> None:
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError()

        async with self.uow:
            repo = WorkspaceAPIKeyRepository(self.uow.session)
            key = await repo.get(key_id)
            if not key or key.workspace_id != workspace_id:
                raise NotFoundError("API Key", key_id)

            key.is_enabled = is_enabled
            await self.uow.commit()

    async def _resolve_key(self, provider_id: str, workspace_id: str, actor: "User", model_name: str = None):
        """Resolves the key for Org scope. Uses model-specific key if set."""
        if model_name:
            stmt = select(WorkspaceModel.api_key_id).where(
                WorkspaceModel.workspace_id == workspace_id,
                WorkspaceModel.provider_id == provider_id,
                WorkspaceModel.model_name == model_name,
                WorkspaceModel.is_enabled == True
            )
            result = await self.uow.session.execute(stmt)
            api_key_id = result.scalar()
            if api_key_id:
                org_repo = WorkspaceAPIKeyRepository(self.uow.session)
                org_key = await org_repo.get(api_key_id)
                if org_key and getattr(org_key, "is_enabled", True):
                    return org_key

        org_repo = WorkspaceAPIKeyRepository(self.uow.session)
        org_key = await org_repo.get_by_org_and_provider(workspace_id, provider_id)
        if org_key and getattr(org_key, "is_enabled", True):
            return org_key
        return None

    async def check_health(
        self, provider_id: str, workspace_id: str, actor: "User"
    ) -> bool:
        async with self.uow:
            key = await self._resolve_key(provider_id, workspace_id, actor)
            if not key:
                raise NotFoundError("API Key", provider_id)
            api_key = decrypt(key.encrypted_key)
            provider = get_provider(provider_id, api_key)
            is_healthy = True
            await self.uow.commit()
            return is_healthy

    async def list_models(
        self, provider_id: str, workspace_id: str, actor: "User"
    ) -> List[Dict[str, str]]:
        async with self.uow:
            key = await self._resolve_key(provider_id, workspace_id, actor)
            if not key:
                return []

            api_key = decrypt(key.encrypted_key)
            provider = get_provider(provider_id, api_key)
            models = await provider.list_models()
            for model in models:
                stmt = select(ModelCapability).where(
                    ModelCapability.provider_id == provider_id,
                    ModelCapability.model_name == model.model_id,
                )
                result = await self.uow.session.execute(stmt)
                if not result.scalar_one_or_none():
                    self.uow.session.add(
                        ModelCapability(
                            provider_id=provider_id,
                            model_name=model.model_id,
                            capabilities={},
                        )
                    )

            await self.uow.commit()
            return models

    async def get_workspace_models(self, workspace_id: str) -> Dict[str, List[Dict[str, str]]]:
        """Return a dict of {provider_id: [{"name": model_name, "api_key_id": api_key_id}, ...]} for a workspace."""
        async with self.uow:
            repo = WorkspaceModelRepository(self.uow.session)
            all_models = await repo.get_all_for_workspace(workspace_id)
            result: Dict[str, List[Dict[str, str]]] = {}
            for m in all_models:
                result.setdefault(m.provider_id, []).append(
                    {"name": m.model_name, "api_key_id": m.api_key_id}
                )
            return result

    async def save_workspace_models(
        self,
        workspace_id: str,
        provider_id: str,
        models: List[str],
        api_key_id: str,
        actor: "User",
    ) -> None:
        """Replace the model list for a specific API key in a workspace. Owner-only."""
        if not await self._is_workspace_owner(actor.id, workspace_id):
            raise ForbiddenError()

        async with self.uow:
            # Delete only models for this specific api_key_id
            stmt = delete(WorkspaceModel).where(
                WorkspaceModel.workspace_id == workspace_id,
                WorkspaceModel.provider_id == provider_id,
                WorkspaceModel.api_key_id == api_key_id
            )
            await self.uow.session.execute(stmt)
            
            for name in models:
                name = name.strip()
                if name:
                    self.uow.session.add(
                        WorkspaceModel(
                            workspace_id=workspace_id,
                            provider_id=provider_id,
                            api_key_id=api_key_id,
                            model_name=name,
                            is_enabled=True,
                        )
                    )
            await self.uow.commit()
