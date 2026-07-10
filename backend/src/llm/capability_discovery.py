import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.models.settings import ModelCapability
from src.llm.capability_manager import ModelCapabilityManager

logger = logging.getLogger(__name__)


def _extract_unsupported_param(error_msg: str, current_kwargs: dict) -> str | None:
    msg = error_msg.lower()
    if "temperature" in msg and (
        "unrecognized" in msg
        or "unsupported" in msg
        or "invalid" in msg
        or "unexpected" in msg
        or "unknown" in msg
        or "does not support" in msg
        or "only the default" in msg
    ):
        return "temperature"
    if "max_tokens" in msg and (
        "unrecognized" in msg
        or "unsupported" in msg
        or "invalid" in msg
        or "unexpected" in msg
        or "unknown" in msg
    ):
        return "max_tokens"
    if "system" in msg and (
        "unrecognized" in msg
        or "unsupported" in msg
        or "invalid" in msg
        or "unexpected" in msg
        or "unknown" in msg
    ):
        return "system_prompt"

    for param in ["temperature", "max_tokens", "system_prompt", "tools"]:
        if param in msg and param in current_kwargs:
            return param

    return None


class DiscoveryService:
    """Handles isolated capability discovery requests."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mcm = ModelCapabilityManager(session)

    async def run_discovery(
        self, provider_id: str, model_name: str, stream_func
    ) -> ModelCapability:
        """
        Runs capability discovery for a model by issuing a test ping.
        """
        cap = await self.mcm.get_or_create_profile(provider_id, model_name)

        if cap.capability_state == "Verified":
            return cap

        cap.capability_state = "Discovering"
        self.session.add(cap)
        await self.session.commit()

        logger.info(f"Starting capability discovery for {provider_id}/{model_name}...")

        test_kwargs = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Say OK"}],
            "temperature": 0.7,
            "max_tokens": 10,
            "stream": True,
        }

        max_attempts = 3

        for attempt in range(max_attempts):
            safe_kwargs = self.mcm.filter_kwargs(test_kwargs, cap)
            try:
                gen = stream_func(**safe_kwargs)
                _ = await anext(gen)

                cap.capability_state = "Verified"
                cap.last_verified = datetime.now(timezone.utc)
                self.session.add(cap)
                await self.session.commit()
                logger.info(
                    f"Capability discovery completed for {model_name}. Profile: {cap.capabilities}"
                )
                return cap

            except StopAsyncIteration:
                cap.capability_state = "Verified"
                cap.last_verified = datetime.now(timezone.utc)
                self.session.add(cap)
                await self.session.commit()
                return cap

            except Exception as e:
                error_msg = str(e)
                removed_param = _extract_unsupported_param(error_msg, safe_kwargs)

                if removed_param:
                    logger.info(
                        f"Discovery found unsupported parameter '{removed_param}' for {model_name}. Retrying..."
                    )
                    new_caps = dict(cap.capabilities)
                    new_caps[removed_param] = False
                    cap.capabilities = new_caps
                    self.session.add(cap)
                    await self.session.commit()
                    continue
                else:
                    logger.error(
                        f"Unrecoverable error during discovery for {model_name}: {error_msg}"
                    )
                    cap.capability_state = "Failed"
                    self.session.add(cap)
                    await self.session.commit()
                    return cap

        cap.capability_state = "Failed"
        self.session.add(cap)
        await self.session.commit()
        return cap
