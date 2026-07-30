from collections.abc import AsyncGenerator

import openai
from src.llm.rag.constant import RAGConstant
from src.providers.llm.openai import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key=api_key)
        self.client = openai.AsyncOpenAI(
            api_key=api_key, base_url="https://openrouter.ai/api/v1"
        )

    async def list_models(self) -> list[dict[str, str]]:
        try:
            models = await self.client.models.list()
            chat_models = []
            for m in models.data:
                chat_models.append({"id": m.id, "name": m.id})
            chat_models.sort(key=lambda x: x["name"])
            return chat_models
        except Exception:  # noqa: BLE001
            return RAGConstant.FALLBACK_OPENROUTER_MODELS

    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        return await super().generate(prompt, system_prompt, **kwargs)

    async def stream(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        async for chunk in super().stream(prompt, system_prompt, **kwargs):
            yield chunk
