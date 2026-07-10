from typing import AsyncGenerator, Dict, List
from groq import AsyncGroq

from src.providers.llm.base import BaseLLMProvider
from src.providers.llm.base import BaseLLMProvider
from src.llm.rag.constant import RAGConstant
from src.core.constants import LLMModelConstants


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = AsyncGroq(api_key=api_key)

    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        model = kwargs.get("model", LLMModelConstants.DEFAULT_GROQ_MODEL)
        messages = kwargs.get("messages")
        if not messages:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        params = {
            "model": model,
            "messages": messages,
        }
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]

        response = await self.client.chat.completions.create(**params)
        return response.choices[0].message.content

    async def stream(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        model = kwargs.get("model", LLMModelConstants.DEFAULT_GROQ_MODEL)
        messages = kwargs.get("messages")
        if not messages:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

        params = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]

        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def list_models(self) -> List[Dict[str, str]]:
        try:
            models = await self.client.models.list()
            return [{"id": m.id, "name": m.id} for m in models.data]
        except Exception:
            return RAGConstant.FALLBACK_GROQ_MODELS

    def supports_streaming(self) -> bool:
        return True
