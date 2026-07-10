from typing import AsyncGenerator, Dict, List
import openai
from src.providers.llm.base import BaseLLMProvider
from src.llm.rag.constant import RAGConstant
import base64


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        model = kwargs.get("model", RAGConstant.OPENAI_DEFAULT_MODEL)
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
        model = kwargs.get("model", RAGConstant.OPENAI_DEFAULT_MODEL)
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

        stream_resp = await self.client.chat.completions.create(**params)
        async for chunk in stream_resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def list_models(self) -> List[Dict[str, str]]:
        try:
            models = await self.client.models.list()
            chat_models = []
            for m in models.data:
                if "gpt" in m.id or "o1" in m.id:
                    chat_models.append({"id": m.id, "name": m.id})
            chat_models.sort(key=lambda x: x["name"])
            return chat_models
        except Exception:
            return RAGConstant.FALLBACK_OPENAI_MODELS

    def supports_streaming(self) -> bool:
        return True
