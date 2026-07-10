import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.settings import ModelCapability

logger = logging.getLogger(__name__)


class FamilyProfileResolver:
    """Provides default capability profiles for well-known model families."""

    @staticmethod
    def resolve(model_name: str) -> Optional[Dict[str, bool]]:
        model = model_name.lower()

        base_caps = {
            "temperature": True,
            "top_p": True,
            "max_tokens": True,
            "system_prompt": True,
            "streaming": True,
            "tools": True,
        }

        if model.startswith(("gpt-", "claude-", "gemini-")):
            return base_caps

        if model.startswith("ollama/"):
            base_caps["tools"] = False
            return base_caps

        return None


class ModelCapabilityManager:
    """Centralized service for managing model capabilities and registry."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_profile(
        self, provider_id: str, model_name: str
    ) -> ModelCapability:
        stmt = select(ModelCapability).where(
            ModelCapability.provider_id == provider_id,
            ModelCapability.model_name == model_name,
        )
        result = await self.session.execute(stmt)
        cap = result.scalar_one_or_none()

        if not cap:
            family_caps = FamilyProfileResolver.resolve(model_name)

            if family_caps is not None:
                state = "Verified"
                caps = family_caps
            else:
                state = "Unknown"
                caps = {}

            cap = ModelCapability(
                provider_id=provider_id,
                model_name=model_name,
                capability_state=state,
                capabilities=caps,
                last_verified=(
                    datetime.now(timezone.utc) if state == "Verified" else None
                ),
            )
            self.session.add(cap)
            await self.session.flush()

        return cap

    def filter_kwargs(
        self, kwargs: Dict[str, Any], cap: ModelCapability
    ) -> Dict[str, Any]:
        """
        Filters kwargs based on known capabilities in the profile.
        If a capability is explicitly False, it is stripped from the request.
        """
        safe_kwargs = {}
        for k, v in kwargs.items():
            if k in ["messages", "model"]:
                safe_kwargs[k] = v
                continue

            is_supported = cap.capabilities.get(k, True)
            if is_supported is not False:
                safe_kwargs[k] = v

        return safe_kwargs

    async def mark_stale_and_update(
        self, cap: ModelCapability, unsupported_param: str
    ) -> None:
        """
        Marks a specific parameter as unsupported and updates the state.
        This allows the system to recover if a provider suddenly changes their API.
        """
        new_caps = dict(cap.capabilities)
        new_caps[unsupported_param] = False
        cap.capabilities = new_caps
        cap.capability_state = "Stale"
        cap.last_verified = datetime.now(timezone.utc)
        self.session.add(cap)
        await self.session.flush()
